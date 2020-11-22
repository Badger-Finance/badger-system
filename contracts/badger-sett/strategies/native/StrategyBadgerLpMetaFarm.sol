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

import "interfaces/curve/ICurveFi.sol";
import "interfaces/curve/ICurveGauge.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";

import "../BaseStrategy.sol";
import "interfaces/uniswap/IStakingRewards.sol";

/*
    Strategy to compound badger rewards
    - Deposit Badger into the vault to receive more from a special rewards pool
*/
contract StrategyBadgerLpMetaFarm is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public geyser;
    address public badger; // Badger Token
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // wBTC Token
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token, used for crv <> weth <> wbtc route

    event HarvestLpMetaFarm(
        uint256 badgerHarvested,
        uint256 totalBadger,
        uint256 badgerConvertedToWbtc,
        uint256 wtbcFromConversion,
        uint256 lpGained,
        uint256 lpDeposited,
        uint256 timestamp,
        uint256 blockNumber
    );

    struct HarvestData {
        uint256 badgerHarvested;
        uint256 totalBadger;
        uint256 badgerConvertedToWbtc;
        uint256 wtbcFromConversion;
        uint256 lpGained;
        uint256 lpDeposited;
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
        geyser = _wantConfig[1];
        badger = _wantConfig[2];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
    }

    /// ===== View Functions =====
    function getName() external override pure returns (string memory) {
        return "StrategyBadgerLpMetaFarm";
    }

    function balanceOfPool() public override view returns (uint256) {
        return IStakingRewards(geyser).balanceOf(address(this));
    }

    function getProtectedTokens() external view override returns (address[] memory) {
        address[] memory protectedTokens = new address[](3);
        protectedTokens[0] = want;
        protectedTokens[1] = geyser;
        protectedTokens[2] = badger;
        return protectedTokens;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(address(geyser) != _asset, "geyser");
        require(address(badger) != _asset, "geyser");
    }

    /// @dev Deposit Badger into the staking contract
    function _deposit(uint256 _want) internal override {
        _safeApproveHelper(want, geyser, _want);
        IStakingRewards(geyser).stake(_want);
    }

    /// @dev Exit stakingRewards position
    /// @dev Harvest all Badger and sent to controller
    function _withdrawAll() internal override {
        IStakingRewards(geyser).exit();

        // Send non-native rewards to controller
        uint256 _badger = IERC20Upgradeable(badger).balanceOf(address(this));
        IERC20Upgradeable(badger).safeTransfer(IController(controller).rewards(), _badger);
    }

    /// @dev Withdraw from staking rewards, using earnings first
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        uint256 _want = IERC20Upgradeable(want).balanceOf(address(this));

        if (_want < _amount) {
            uint256 _toWithdraw = _amount.sub(_want);
            IStakingRewards(geyser).withdraw(_toWithdraw);
        }

        return _amount;
    }

    /// @dev Harvest accumulated badger rewards and convert them to LP tokens
    /// @dev Restake the gained LP tokens in the Geyser
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _beforeBadger = IERC20Upgradeable(badger).balanceOf(address(this));
        uint256 _beforeLp = IERC20Upgradeable(want).balanceOf(address(this));

        // Harvest rewards from Geyser
        IStakingRewards(geyser).getReward();

        harvestData.totalBadger = IERC20Upgradeable(badger).balanceOf(address(this));
        harvestData.badgerHarvested = harvestData.totalBadger.sub(_beforeBadger);

        // Swap half of harvested badger for wBTC in liquidity pool
        if (harvestData.totalBadger > 0) {
            harvestData.badgerConvertedToWbtc = harvestData.badgerHarvested.div(2);
            if (harvestData.badgerConvertedToWbtc > 0) {
                address[] memory path = new address[](2);
                path[0] = badger; // Badger
                path[1] = wbtc;

                _swap(badger, harvestData.badgerConvertedToWbtc, path);

                // Add Badger and wBTC as liquidity if any to add
                _add_max_liquidity_uniswap(badger, wbtc);
            }
        }

        // Deposit gained LP position into staking rewards
        harvestData.lpDeposited = IERC20Upgradeable(want).balanceOf(address(this));
        harvestData.lpGained = harvestData.lpDeposited.sub(_beforeLp);
        if (harvestData.lpGained > 0) {
            _deposit(harvestData.lpGained);
        }

        emit HarvestLpMetaFarm(
            harvestData.badgerHarvested,
            harvestData.totalBadger,
            harvestData.badgerConvertedToWbtc,
            harvestData.wtbcFromConversion,
            harvestData.lpGained,
            harvestData.lpDeposited,
            block.timestamp,
            block.number
        );
        emit Harvest(harvestData.lpGained, block.number);

        return harvestData;
    }
}
