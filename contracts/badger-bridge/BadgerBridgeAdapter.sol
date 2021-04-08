// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";

import "interfaces/badger/ISwapStrategyRouter.sol";
import "interfaces/bridge/IGateway.sol";
import "interfaces/bridge/IBridgeVault.sol";
import "interfaces/curve/ICurveFi.sol";

contract BadgerBridgeAdapter is OwnableUpgradeable, ReentrancyGuardUpgradeable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20 for IERC20;

    IERC20 public renBTC;
    IERC20 public wBTC;

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

    mapping(address => bool) public approvedVaults;

    // Make struct for mint args, otherwise too many local vars (stack too deep).
    struct MintArguments {
        uint256 _mintAmount;
        uint256 _mintAmountMinusFee;
        uint256 _fee;
        uint256 _slippage;
        address _vault;
        address _user;
        address _token;
    }

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

    function version() external view returns (string memory) {
        return "1.1";
    }

    // NB: This recovery fn only works for the BTC gateway (hardcoded and only one supported in this adapter).
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
        address _user,
        address _vault,
        // darknode args
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external nonReentrant {
        require(_token == address(renBTC) || _token == address(wBTC), "invalid token address");

        // Mint renBTC tokens
        bytes32 pHash = keccak256(abi.encode(_token, _slippage, _user, _vault));
        uint256 mintAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);

        require(mintAmount > 0, "zero mint amount");

        uint256 fee = _processFee(renBTC, mintAmount, mintFeeBps);
        uint256 mintAmountMinusFee = mintAmount.sub(fee);

        MintArguments memory args = MintArguments(mintAmount, mintAmountMinusFee, fee, _slippage, _vault, _user, _token);
        (bool success, ) = address(this).call(abi.encodeWithSelector(this.mintAdapter.selector, args));

        if (!success) {
            renBTC.safeTransfer(_user, mintAmountMinusFee);
        }
    }

    function burn(
        // user args
        address _token, // either renBTC or wBTC
        address _vault,
        uint256 _slippage,
        bytes calldata _btcDestination,
        uint256 _amount
    ) external nonReentrant {
        require(_token == address(renBTC) || _token == address(wBTC), "invalid token address");
        require(!(_vault != address(0) && !approvedVaults[_vault]), "Vault not approved");

        bool isVault = _vault != address(0);
        bool isRenBTC = _token == address(renBTC);
        IERC20 token = isRenBTC ? renBTC : wBTC;
        uint256 startBalanceRenBTC = renBTC.balanceOf(address(this));
        uint256 startBalanceWBTC = wBTC.balanceOf(address(this));

        if (isVault) {
            IERC20(_vault).safeTransferFrom(msg.sender, address(this), _amount);
            IBridgeVault(_vault).withdraw(IERC20(_vault).balanceOf(address(this)));
        } else {
            token.safeTransferFrom(msg.sender, address(this), _amount);
        }

        uint256 wbtcTransferred = wBTC.balanceOf(address(this)).sub(startBalanceWBTC);

        if (!isRenBTC) {
            _swapWBTCForRenBTC(wbtcTransferred, _slippage);
        }

        uint256 toBurnAmount = renBTC.balanceOf(address(this)).sub(startBalanceRenBTC);
        uint256 fee = _processFee(renBTC, toBurnAmount, burnFeeBps);

        emit Burn(toBurnAmount, wbtcTransferred, fee);

        uint256 burnAmount = registry.getGatewayBySymbol("BTC").burn(_btcDestination, toBurnAmount.sub(fee));
    }

    function mintAdapter(MintArguments memory args) external {
        require(msg.sender == address(this), "Not itself");
        require(!(args._vault != address(0) && !approvedVaults[args._vault]), "Vault not approved");

        uint256 wbtcExchanged;
        bool isVault = args._vault != address(0);
        bool isRenBTC = args._token == address(renBTC);
        IERC20 token = isRenBTC ? renBTC : wBTC;

        if (!isRenBTC) {
            // Try and swap and transfer wbtc if token wbtc specified.
            uint256 startBalance = token.balanceOf(address(this));
            if (_swapRenBTCForWBTC(args._mintAmountMinusFee, args._slippage)) {
                uint256 endBalance = token.balanceOf(address(this));
                wbtcExchanged = endBalance.sub(startBalance);
            }
        }

        emit Mint(args._mintAmount, wbtcExchanged, args._fee);

        uint256 amount = isRenBTC ? args._mintAmountMinusFee : wbtcExchanged;

        if (args._vault == address(0)) {
            token.safeTransfer(args._user, amount);
            return;
        }

        // Maybe deposit into curve lp pool if vault accepts a curve lp token.
        // We currently only supply liquidity as renBTC (see fn comment).
        bool depositedToCurve = _maybeDepositCurveLp(args._vault, token, amount);
        if (!depositedToCurve) {
            // If we didn't deposit to curve, then we're depositing `token` directly
            // to the underlying vault (e.g. wbtc vault) so we need to approve token spend.
            _approveBalance(token, args._vault, token.balanceOf(address(this)));
        }

        IBridgeVault(args._vault).deposit(amount);
        IERC20(args._vault).safeTransfer(args._user, IERC20(args._vault).balanceOf(address(this)));
    }

    // NB: We currently only support curve lp pools that have renBTC as an asset.
    // We supply liquidity as renBTC to these pools. Some lp pools require two deposits
    // as they are a pool of other pool tokens (e.g. tbtc).
    //
    // We could allow dynamic configuration of curve pools to vaults but this will be a
    // little more gas intensive to do so the logic is hard coded for now.
    //
    // Currently supported lp pools are:
    // - renbtc
    // - sbtc
    // - tbtc (requires deposiitng into sbtc lp pool first)
    function _maybeDepositCurveLp(
        address _vault,
        IERC20 _token,
        uint256 _amount
    ) internal returns (bool) {
        if (_token != renBTC) {
            return false;
        }

        IERC20 vaultToken = IBridgeVault(_vault).token();
        // Define supported tokens here to avoid proxy storage.
        IERC20 renbtcLpToken = IERC20(0x49849C98ae39Fff122806C06791Fa73784FB3675);
        IERC20 sbtcLpToken = IERC20(0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3);
        IERC20 tbtcLpToken = IERC20(0x64eda51d3Ad40D56b9dFc5554E06F94e1Dd786Fd);

        // Pool contracts are not upgradeable so no need to sanity check underlying token addrs.
        address pool;

        if (vaultToken == renbtcLpToken) {
            pool = 0x93054188d876f558f4a66B2EF1d97d16eDf0895B;
            uint256[2] memory amounts = [_amount, 0];
            _approveBalance(renBTC, pool, _amount);
            ICurveFi(pool).add_liquidity(amounts, 0);
        }

        if (vaultToken == sbtcLpToken || vaultToken == tbtcLpToken) {
            pool = 0x7fC77b5c7614E1533320Ea6DDc2Eb61fa00A9714;
            uint256[3] memory amounts = [_amount, 0, 0];
            _approveBalance(renBTC, pool, _amount);
            ICurveFi(pool).add_liquidity(amounts, 0);
        }

        if (vaultToken == tbtcLpToken) {
            pool = 0xC25099792E9349C7DD09759744ea681C7de2cb66;
            uint256 lpAmount = sbtcLpToken.balanceOf(address(this));
            uint256[2] memory amounts = [0, lpAmount];
            _approveBalance(sbtcLpToken, pool, lpAmount);
            ICurveFi(pool).add_liquidity(amounts, 0);
        }

        _approveBalance(vaultToken, _vault, vaultToken.balanceOf(address(this)));

        return pool != address(0x0);
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
            // Do not swap if slippage is too high;
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
        return _amount.mul(_slippage).div(1e4);
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

    function _approveBalance(
        IERC20 _token,
        address _spender,
        uint256 _amount
    ) internal {
        if (_token.allowance(address(this), _spender) < _amount) {
            // Approve max spend.
            _token.approve(_spender, (1 << 64) - 1);
        }
    }

    // Admin methods.
    function setMintFeeBps(uint256 _mintFeeBps) external onlyOwner {
        require(_mintFeeBps <= MAX_BPS, "badger-bridge-adapter/excessive-mint-fee");
        mintFeeBps = _mintFeeBps;
    }

    function setBurnFeeBps(uint256 _burnFeeBps) external onlyOwner {
        require(_burnFeeBps <= MAX_BPS, "badger-bridge-adapter/excessive-burn-fee");
        burnFeeBps = _burnFeeBps;
    }

    function setPercentageFeeGovernanceBps(uint256 _percentageFeeGovernanceBps) external onlyOwner {
        require(_percentageFeeGovernanceBps + percentageFeeRewardsBps <= MAX_BPS, "badger-bridge-adapter/excessive-percentage-fee-governance");
        percentageFeeGovernanceBps = _percentageFeeGovernanceBps;
    }

    function setPercentageFeeRewardsBps(uint256 _percentageFeeRewardsBps) external onlyOwner {
        require(_percentageFeeRewardsBps + percentageFeeGovernanceBps <= MAX_BPS, "badger-bridge-adapter/excessive-percentage-fee-rewards");
        percentageFeeRewardsBps = _percentageFeeRewardsBps;
    }

    function setRewards(address _rewards) external onlyOwner {
        rewards = _rewards;
    }

    function setRouter(address _router) external onlyOwner {
        router = ISwapStrategyRouter(_router);
    }

    function setRegistry(address _registry) external onlyOwner {
        registry = IGatewayRegistry(_registry);
        renBTC = registry.getTokenBySymbol("BTC");
    }

    function setVaultApproval(address _vault, bool _status) external onlyOwner {
        approvedVaults[_vault] = _status;
    }
}
