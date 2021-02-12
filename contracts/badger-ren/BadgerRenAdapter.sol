// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";

import "interfaces/ren/IGateway.sol";
import "interfaces/curve/ICurveExchange.sol";

// TOOD: Refactor out swap logic.
// TOOD: Unify mint/burn API methods.
contract BadgerRenAdapter is OwnableUpgradeable, ReentrancyGuardUpgradeable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20 for IERC20;

    IERC20 renBTC;
    IERC20 wBTC;

    // RenVM gateway registry.
    IGatewayRegistry public registry;
    // Curve exchange contract for the renBTC/wBTC pool.
    ICurveExchange public exchange;

    event RecoverStuckRenBTC(uint256 amount, uint256 fee);
    event MintRenBTC(uint256 amount, uint256 fee);
    event BurnRenBTC(uint256 amount, uint256 fee);
    event MintWBTC(uint256 renbtc_minted, uint256 wbtc_exchanged, uint256 fee);
    event BurnWBTC(uint256 wbtc_transferred, uint256 renbtc_burned, uint256 fee);
    event ExchangeWBTCBytesError(bytes error);
    event ExchangeWBTCStringError(string error);

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
        address _exchange,
        address _wbtc,
        uint256[4] memory _feeConfig
    ) public initializer {
        __Ownable_init_unchained();
        governance = _governance;
        rewards = _rewards;

        registry = IGatewayRegistry(_registry);
        exchange = ICurveExchange(_exchange);
        renBTC = registry.getTokenBySymbol("BTC");
        wBTC = IERC20(_wbtc);

        mintFeeBps = _feeConfig[0];
        burnFeeBps = _feeConfig[1];
        percentageFeeRewardsBps = _feeConfig[2];
        percentageFeeGovernanceBps = _feeConfig[3];

        // Approve exchange.
        require(renBTC.approve(_exchange, uint256(-1)));
        require(wBTC.approve(_exchange, uint256(-1)));
    }

    function recoverStuck(
        bytes calldata encoded,
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

        emit RecoverStuckRenBTC(_mintAmount, _fee);

        renBTC.safeTransfer(msg.sender, _mintAmount.sub(_fee));
    }

    function mintRenBTC(
        // user args
        address payable _destination,
        // darknode args
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external nonReentrant {
        // Mint renBTC tokens
        bytes32 pHash = keccak256(abi.encode(_destination));
        uint256 _mintAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);
        uint256 _fee = _processFee(renBTC, _mintAmount, mintFeeBps);

        emit MintRenBTC(_mintAmount, _fee);

        renBTC.safeTransfer(_destination, _mintAmount.sub(_fee));
    }

    function burnRenBTC(bytes calldata _btcDestination, uint256 _amount) external nonReentrant {
        require(renBTC.balanceOf(address(msg.sender)) >= _amount);
        uint256 _startBalance = renBTC.balanceOf(address(this));
        renBTC.safeTransferFrom(msg.sender, address(this), _amount);
        uint256 _endBalance = renBTC.balanceOf(address(this));

        uint256 _burnAmount = _endBalance.sub(_startBalance);
        uint256 _fee = _processFee(renBTC, _burnAmount, burnFeeBps);

        emit BurnRenBTC(_burnAmount, _fee);

        uint256 burnAmount = registry.getGatewayBySymbol("BTC").burn(_btcDestination, _burnAmount.sub(_fee));
    }

    function mintWBTC(
        uint256 _slippage,
        address payable _destination,
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external nonReentrant {
        // Mint renBTC tokens
        bytes32 pHash = keccak256(abi.encode(_slippage, _destination));
        uint256 _mintAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);
        _swapRenBTCForWBTC(_slippage, _destination, _mintAmount);
    }

    function _swapRenBTCForWBTC(
        uint256 _slippage,
        address payable _destination,
        uint256 _mintAmount
    ) internal {
        // Get price
        uint256 dy = exchange.get_dy(0, 1, _mintAmount);
        _slippage = uint256(1e4).sub(_slippage);
        uint256 min_dy = dy.mul(_slippage).div(1e4);

        uint256 _startBalance = wBTC.balanceOf(address(this));
        try exchange.exchange(0, 1, _mintAmount, min_dy)  {
            uint256 _endBalance = wBTC.balanceOf(address(this));
            uint256 _wbtcAmount = _endBalance.sub(_startBalance);
            uint256 _fee = _processFee(wBTC, _wbtcAmount, mintFeeBps);
            emit MintWBTC(_mintAmount, _wbtcAmount, _fee);

            // Send converted wBTC to user.
            wBTC.safeTransfer(_destination, _wbtcAmount.sub(_fee));
            // Return immediately if transfer success.
            return;
        } catch Error(string memory _error) {
            emit ExchangeWBTCStringError(_error);
        } catch (bytes memory _error) {
            emit ExchangeWBTCBytesError(_error);
        }
        _fallbackTransferRenBTC(_destination, _mintAmount);
    }

    function burnWBTC(
        bytes calldata _btcDestination,
        uint256 _amount,
        uint256 _minAmount
    ) external nonReentrant {
        wBTC.safeTransferFrom(msg.sender, address(this), _amount);
        uint256 _startBalance = renBTC.balanceOf(address(this));
        exchange.exchange(1, 0, _amount, _minAmount);
        uint256 _endBalance = renBTC.balanceOf(address(this));

        uint256 _burnAmount = _endBalance.sub(_startBalance);
        uint256 _fee = _processFee(renBTC, _burnAmount, burnFeeBps);

        // Burn and send proceeds to the User
        uint256 burnAmount = registry.getGatewayBySymbol("BTC").burn(_btcDestination, _burnAmount.sub(_fee));
        emit BurnWBTC(_amount, burnAmount, _fee);
    }

    // _fallbackTransferRenBTC transfers minted renBTC to user when an exchange fails.
    function _fallbackTransferRenBTC(address _destination, uint256 _amount) internal {
        uint256 _fee = _processFee(renBTC, _amount, mintFeeBps);
        emit MintRenBTC(_amount, _fee);
        renBTC.safeTransfer(_destination, _amount.sub(_fee));
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
