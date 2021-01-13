// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/uniswap/IUniswapV2Factory.sol";
import "interfaces/badger/IBadgerGeyser.sol";
import "interfaces/digg/IDigg.sol";

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/uniswap/IUniswapV2Pair.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";

import "../BaseStrategySwapper.sol";
import "interfaces/uniswap/IStakingRewards.sol";

/*
    ===== StrategyDiggLpMetaFarm =====
    - Harvest DIGG from special rewards pool and sell to increase LP Position
*/
contract StrategyDiggLpMetaFarm is BaseStrategyMultiSwapper {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public diggFaucet;
    address public digg; // Digg Token
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // wBTC Token, directly paired with digg

    event HarvestLpMetaFarm(
        uint256 totalDigg,
        uint256 totalShares,
        uint256 sharesHarvested,
        uint256 diggToStrategist,
        uint256 diggToGovernance,
        uint256 sharesConvertedToWbtc,
        uint256 diggConvertedToWbtc,
        uint256 wtbcFromConversion,
        uint256 lpDeposited,
        uint256 lpGained,
        uint256 timestamp,
        uint256 blockNumber
    );

    struct HarvestData {
        uint256 totalDigg;
        uint256 totalShares;
        uint256 sharesHarvested;
        uint256 diggToStrategist;
        uint256 diggToGovernance;
        uint256 sharesConvertedToWbtc;
        uint256 diggConvertedToWbtc;
        uint256 wtbcFromConversion;
        uint256 lpDeposited;
        uint256 lpGained;
    }

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[3] memory _wantConfig,
        uint256[3] memory _feeConfig
    ) public initializer {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        diggFaucet = _wantConfig[1];
        digg = _wantConfig[2];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
    }

    /// ===== View Functions =====
    function getName() external override pure returns (string memory) {
        return "StrategyDiggLpMetaFarm";
    }

    function balanceOfPool() public override view returns (uint256) {
        return IERC20Upgradeable(want).balanceOf(address(this));
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](3);
        protectedTokens[0] = want;
        protectedTokens[1] = diggFaucet;
        protectedTokens[2] = digg;
        return protectedTokens;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(address(diggFaucet) != _asset, "diggFaucet");
        require(address(digg) != _asset, "digg");
    }

    /// @dev No need to stake uni lp.
    function _deposit(uint256 _want) internal override {}

    /// @dev No active position, just send all want to controller as per wrapper withdrawAll() function
    /// @dev Do harvest all pending DIGG rewards and send to controller rewards
    function _withdrawAll() internal override {
        IStakingRewards(diggFaucet).getReward();

        uint256 _diggBalance = IDigg(digg).balanceOf(address(this));
        // Send DIGG rewards to controller
        IDigg(digg).transfer(IController(controller).rewards(), _diggBalance);

        // Note: All want in contract will be sent in wrapper function
    }

    /// @dev Stra
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        // We only have idle want, withdraw from the strategy directly
        return _amount;
    }

    /// @dev Harvest accumulated digg rewards and convert them to LP tokens
    /// @dev Restake the gained LP tokens in the Geyser
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _beforeDigg = IDigg(want).balanceOf(address(this));
        uint256 _beforeShares = IDigg(want).sharesOf(address(this));
        uint256 _beforeLp = IERC20Upgradeable(want).balanceOf(address(this));

        // ===== Harvest rewards from Geyser =====
        IStakingRewards(diggFaucet).getReward();

        harvestData.totalDigg = IDigg(digg).balanceOf(address(this));
        harvestData.totalShares = IDigg(digg).sharesOf(address(this));
        harvestData.sharesHarvested = harvestData.totalShares.sub(_beforeShares);

        // Process performance fees if present
        harvestData.diggToStrategist = _processFee(digg, harvestData.totalDigg, performanceFeeStrategist, strategist);
        harvestData.diggToGovernance = _processFee(digg, harvestData.totalDigg, performanceFeeGovernance, IController(controller).rewards());

        // Swap half of harvested digg for wBTC in liquidity pool
        if (harvestData.totalShares > 0) {
            harvestData.sharesConvertedToWbtc = harvestData.sharesHarvested.div(2);

            if (harvestData.sharesConvertedToWbtc > 0) {
                address[] memory path = new address[](2);
                path[0] = digg;
                path[1] = wbtc;

                // We use actual DIGG balance in trade rather than shares
                harvestData.diggConvertedToWbtc = IDigg(digg).sharesToFragments(harvestData.sharesConvertedToWbtc);

                // Note: We must sync before trading due to having a rebasing asset in the pair
                address pair = _get_uni_pair(digg, wbtc);
                IUniswapV2Pair(pair).sync();

                _swap(digg, harvestData.diggConvertedToWbtc, path);

                harvestData.wtbcFromConversion = IERC20Upgradeable(wbtc).balanceOf(address(this));

                // Add Digg and wBTC as liquidity if any to add
                _add_max_liquidity_uniswap(digg, wbtc);
            }
        }

        // ===== Deposit gained LP position =====
        harvestData.lpDeposited = IERC20Upgradeable(want).balanceOf(address(this));
        harvestData.lpGained = harvestData.lpDeposited.sub(_beforeLp);

        // Note: No active position for this strategy, keep LP gains in strategy itself

        emit HarvestLpMetaFarm(
            harvestData.totalDigg,
            harvestData.totalShares,
            harvestData.sharesHarvested,
            harvestData.diggToStrategist,
            harvestData.diggToGovernance,
            harvestData.sharesConvertedToWbtc,
            harvestData.diggConvertedToWbtc,
            harvestData.wtbcFromConversion,
            harvestData.lpDeposited,
            harvestData.lpGained,
            block.timestamp,
            block.number
        );
        emit Harvest(harvestData.lpGained, block.number);

        return harvestData;
    }
}
