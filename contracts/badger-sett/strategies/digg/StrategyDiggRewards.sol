// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IBadgerGeyser.sol";

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";

import "../BaseStrategy.sol";
import "interfaces/badger/IStrategy.sol";
import "interfaces/uniswap/IStakingRewards.sol";
import "interfaces/digg/IDigg.sol";

/*
    Strategy to compound DIGG rewards
    - Deposit DIGG into the vault to receive more DIGG from a special rewards pool
    - bDIGG is a non-rebasing asset that can be composed into other systems more easily
*/
contract StrategyDiggRewards is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public diggFaucet;

    struct HarvestData {
        uint256 totalDigg;
        uint256 totalShares;
        uint256 totalScaledShares;
        uint256 diggIncrease;
        uint256 sharesIncrease;
        uint256 scaledSharesIncrease;
    }

    event HarvestState (
        uint256 totalDigg,
        uint256 totalShares,
        uint256 totalScaledShares,
        uint256 diggIncrease,
        uint256 sharesIncrease,
        uint256 scaledSharesIncrease
    );

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[2] memory _wantConfig,
        uint256[3] memory _feeConfig
    ) public initializer {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        diggFaucet = _wantConfig[1];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
    }

    /// ===== View Functions =====
    function getName() external override pure returns (string memory) {
        return "StrategyDiggRewards";
    }

    function version() external pure returns (string memory) {
        return "1.0";
    }

    /// @dev No strategy positions for the native rewards strategy
    function balanceOfPool() public override view returns (uint256) {
        return 0;
    }

    /// @dev No strategy positions for the native rewards strategy
    function sharesOfPool() public view returns (uint256) {
        return 0;
    }

    function sharesOfWant() public view returns (uint256) {
        return IDigg(want).sharesOf(address(this));
    }

    function sharesOf() public view returns (uint256) {
        return sharesOfWant().add(sharesOfPool());
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](1);
        protectedTokens[0] = want;
        return protectedTokens;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
    }

    /// @notice No active position
    function _deposit(uint256 _want) internal override {
    }

    /// @dev No active position to exit, just send all want to controller as per wrapper withdrawAll() function
    /// @dev Do harvest all pending DIGG rewards before, will be sent with want transfer
    function _withdrawAll() internal override {
        IStakingRewards(diggFaucet).getReward();
    }

    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        // We only have idle DIGG, withdraw from the strategy directly
        // Note: This value is in DIGG fragments
        return _amount;
    }

    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _beforeDigg = IDigg(want).balanceOf(address(this));
        uint256 _beforeShares = IDigg(want).sharesOf(address(this));
        uint256 _beforeScaledShares = IDigg(want).sharesToScaledShares(_beforeShares);

        // ===== Harvest rewards from Geyser =====
        IStakingRewards(diggFaucet).getReward();
        
        harvestData.totalDigg = IDigg(want).balanceOf(address(this));
        harvestData.totalShares = IDigg(want).sharesOf(address(this));
        harvestData.totalScaledShares = IDigg(want).sharesToScaledShares(harvestData.totalShares);

        harvestData.diggIncrease = harvestData.totalDigg.sub(_beforeDigg);
        harvestData.sharesIncrease = harvestData.totalShares.sub(_beforeShares);
        harvestData.scaledSharesIncrease = harvestData.totalScaledShares.sub(_beforeScaledShares);

        emit Harvest(harvestData.sharesIncrease, block.number);
        emit HarvestState(
            harvestData.totalDigg,
            harvestData.totalShares,
            harvestData.totalScaledShares,
            harvestData.diggIncrease,
            harvestData.sharesIncrease,
            harvestData.scaledSharesIncrease
        );

        return harvestData;
    }
}
