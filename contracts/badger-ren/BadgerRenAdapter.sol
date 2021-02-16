// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";

import "interfaces/badger/ISwapStrategyRouter.sol";
import "interfaces/ren/IGateway.sol";

contract BadgerRenAdapter is OwnableUpgradeable, ReentrancyGuardUpgradeable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20 for IERC20;

    IERC20 renBTC;
    IERC20 wBTC;

    // RenVM gateway registry.
    IGatewayRegistry public registry;
    // Swap router that handles swap routing optimizations.
    ISwapStrategyRouter public router;

    event RecoverStuck(uint256 amount, uint256 fee);
    event Mint(uint256 renbtc_minted, uint256 wbtc_swapped, uint256 fee);
    event Burn(uint256 renbtc_burned, uint256 wbtc_transferred, uint256 fee);
    event SwapError(bytes error);

    address public rewards;
    address public governance;

    uint256 public mintFeeBps;
    uint256 public burnFeeBps;
    uint256 private percentageFeeRewardsBps;
    uint256 private percentageFeeGovernanceBps;

    uint256 public constant MAX_BPS = 10000;

    function initialize(
        address _governance,
        address _rewards,
        address _registry,
        address _router,
        address _wbtc,
        uint256[4] memory _feeConfig
    ) public initializer {
        __Ownable_init();
        __ReentrancyGuard_init();

        require(_governance != address(0x0), "must set governance address");
        require(_rewards != address(0x0), "must set rewards address");
        require(_registry != address(0x0), "must set registry address");
        require(_router != address(0x0), "must set router address");
        require(_wbtc != address(0x0), "must set wBTC address");

        governance = _governance;
        rewards = _rewards;

        registry = IGatewayRegistry(_registry);
        router = ISwapStrategyRouter(_router);
        renBTC = registry.getTokenBySymbol("BTC");
        wBTC = IERC20(_wbtc);

        mintFeeBps = _feeConfig[0];
        burnFeeBps = _feeConfig[1];
        percentageFeeRewardsBps = _feeConfig[2];
        percentageFeeGovernanceBps = _feeConfig[3];
    }

    function recoverStuck(
        // encoded user args
        bytes calldata encoded,
        // darkdnode args
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external nonReentrant {
        // Ensure sender matches sender of original tx.
        uint256 start = encoded.length - 32;
        address sender = abi.decode(encoded[start:], (address));
        require(sender == msg.sender);

        bytes32 pHash = keccak256(encoded);
        uint256 _mintAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);
        uint256 _fee = _processFee(renBTC, _mintAmount, mintFeeBps);

        emit RecoverStuck(_mintAmount, _fee);

        renBTC.safeTransfer(msg.sender, _mintAmount.sub(_fee));
    }

    function mint(
        // user args
        address _token, // either renBTC or wBTC
        uint256 _slippage,
        address payable _destination,
        // darknode args
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external nonReentrant {
        require(_token == address(renBTC) || _token == address(wBTC), "invalid token address");

        // Mint renBTC tokens
        bytes32 pHash = keccak256(abi.encode(_token, _slippage, _destination));
        uint256 mintAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);
        uint256 fee = _processFee(renBTC, mintAmount, mintFeeBps);
        uint256 mintAmountMinusFee = mintAmount.sub(fee);

        uint256 wbtcExchanged;
        if (_token == address(wBTC)) {
            // Try and swap and transfer wbtc if token wbtc specified.
            uint256 startBalance = wBTC.balanceOf(address(this));
            if (_swapRenBTCForWBTC(mintAmountMinusFee, _slippage)) {
                uint256 endBalance = wBTC.balanceOf(address(this));
                wbtcExchanged = endBalance.sub(startBalance);
                wBTC.safeTransfer(_destination, wbtcExchanged);
                emit Mint(mintAmount, wbtcExchanged, fee);
                return;
            }
        }

        emit Mint(mintAmount, wbtcExchanged, fee);

        renBTC.safeTransfer(_destination, mintAmountMinusFee);
    }

    function burn(
        // user args
        address _token, // either renBTC or wBTC
        uint256 _slippage,
        bytes calldata _btcDestination,
        uint256 _amount
    ) external nonReentrant {
        require(_token == address(renBTC) || _token == address(wBTC), "invalid token address");

        uint256 wbtcTransferred;
        uint256 startBalance = renBTC.balanceOf(address(this));

        if (_token == address(renBTC)) {
            require(renBTC.balanceOf(address(msg.sender)) >= _amount);
            renBTC.safeTransferFrom(msg.sender, address(this), _amount);
        }

        if (_token == address(wBTC)) {
            wBTC.safeTransferFrom(msg.sender, address(this), _amount);
            wbtcTransferred = _amount;
            _swapWBTCForRenBTC(_amount, _slippage);
        }

        uint256 endBalance = renBTC.balanceOf(address(this));
        uint256 toBurnAmount = endBalance.sub(startBalance);
        uint256 fee = _processFee(renBTC, toBurnAmount, burnFeeBps);

        emit Burn(toBurnAmount, wbtcTransferred, fee);

        uint256 burnAmount = registry.getGatewayBySymbol("BTC").burn(_btcDestination, toBurnAmount.sub(fee));
        require(toBurnAmount.sub(fee) == burnAmount, "burned amount does not match to burn amount minus fees");
    }

    function _swapWBTCForRenBTC(uint256 _amount, uint256 _slippage) internal {
        (address strategy, uint256 estimatedAmount) = router.optimizeSwap(address(wBTC), address(renBTC), _amount);
        uint256 minAmount = _minAmount(_slippage, _amount);
        require(estimatedAmount > minAmount, "slippage too high");

        // Transfer wBTC to strategy so strategy can complete the swap.
        wBTC.safeTransfer(strategy, _amount);
        uint256 amount = ISwapStrategy(strategy).swapTokens(address(wBTC), address(renBTC), _amount, _slippage);
        require(amount > minAmount, "swapped amount less than min amount");
    }

    // Avoid reverting on mint (renBTC -> wBTC swap) since we cannot roll back that transaction.:
    function _swapRenBTCForWBTC(uint256 _amount, uint256 _slippage) internal returns (bool) {
        (address strategy, uint256 estimatedAmount) = router.optimizeSwap(address(renBTC), address(wBTC), _amount);
        uint256 minAmount = _minAmount(_slippage, _amount);
        if (minAmount > estimatedAmount) {
            // Do not swap if slippage is too high>
            return false;
        }

        // Transfer renBTC to strategy so strategy can complete the swap.
        renBTC.safeTransfer(strategy, _amount);
        try ISwapStrategy(strategy).swapTokens(address(renBTC), address(wBTC), _amount, _slippage)  {
            return true;
        } catch (bytes memory _error) {
            emit SwapError(_error);
            return false;
        }
    }

    // Minimum amount w/ slippage applied.
    function _minAmount(uint256 _slippage, uint256 _amount) internal returns (uint256) {
        _slippage = uint256(1e4).sub(_slippage);
        return _amount.div(_slippage).mul(1e4);
    }

    function _processFee(
        IERC20 token,
        uint256 amount,
        uint256 feeBps
    ) internal returns (uint256) {
        if (feeBps == 0) {
            return 0;
        }
        uint256 fee = amount.mul(feeBps).div(MAX_BPS);
        uint256 governanceFee = fee.mul(percentageFeeGovernanceBps).div(MAX_BPS);
        uint256 rewardsFee = fee.mul(percentageFeeRewardsBps).div(MAX_BPS);
        IERC20(token).safeTransfer(governance, governanceFee);
        IERC20(token).safeTransfer(rewards, rewardsFee);
        return fee;
    }

    // Admin methods.
    function setMintFeeBps(uint256 _mintFeeBps) external onlyOwner {
        require(_mintFeeBps <= MAX_BPS, "badger-ren-adapter/excessive-mint-fee");
        mintFeeBps = _mintFeeBps;
    }

    function setBurnFeeBps(uint256 _burnFeeBps) external onlyOwner {
        require(_burnFeeBps <= MAX_BPS, "badger-ren-adapter/excessive-burn-fee");
        burnFeeBps = _burnFeeBps;
    }

    function setPercentageFeeGovernanceBps(uint256 _percentageFeeGovernanceBps) external onlyOwner {
        require(_percentageFeeGovernanceBps + percentageFeeRewardsBps <= MAX_BPS, "badger-ren-adapter/excessive-percentage-fee-governance");
        percentageFeeGovernanceBps = _percentageFeeGovernanceBps;
    }

    function setPercentageFeeRewardsBps(uint256 _percentageFeeRewardsBps) external onlyOwner {
        require(_percentageFeeRewardsBps + percentageFeeGovernanceBps <= MAX_BPS, "badger-ren-adapter/excessive-percentage-fee-rewards");
        percentageFeeRewardsBps = _percentageFeeRewardsBps;
    }

    function setRewards(address _rewards) external onlyOwner {
        rewards = _rewards;
    }
}
