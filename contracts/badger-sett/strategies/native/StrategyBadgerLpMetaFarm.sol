// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

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

    event Harvest(uint256 preBadgerBalance, uint256 harvestedBadger, uint256 preWantBalance, uint256 liquidityAdded);

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

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(address(geyser) != _asset, "geyser");
    }

    /// @dev Deposit Badger into the staking contract
    function _deposit(uint256 _want) internal override {
        IStakingRewards(geyser).stake(_want);
    }

    /// @dev Harvest all Badger and sent to controller
    function _withdrawAll() internal override {
        IStakingRewards(geyser).exit();
    }

    /// @dev Withdraw from staking rewards, using earnings first
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        uint256 _earned = IStakingRewards(geyser).earned(address(this));

        if (_earned < _amount) {
            IStakingRewards(geyser).withdraw(_amount.sub(_earned));
        }

        return _amount;
    }

    /// @dev Harvest accumulated badger rewards and convert them to LP tokens
    function harvest() external override {
        _onlyAuthorizedActors();

        uint256 _beforeBadger = IERC20Upgradeable(badger).balanceOf(address(this));
        IStakingRewards(geyser).getReward();

        uint256 _afterBadger = IERC20Upgradeable(badger).balanceOf(address(this));
        uint256 _harvested = _afterBadger.sub(_beforeBadger);

        address[] memory path = new address[](3);
        path[0] = badger; // Badger
        path[1] = weth;
        path[2] = wbtc;

        uint256 _beforeLp = IERC20Upgradeable(want).balanceOf(address(this));

        // Swap half of harvested badger for wBTC and add as liquidity
        _swap(badger, _harvested.div(2), path);
        _add_liquidity(want, wbtc);

        uint256 _afterLp = IERC20Upgradeable(want).balanceOf(address(this));

        emit Harvest(_beforeBadger, _harvested, _beforeLp, _afterLp.sub(_beforeLp));
    }
}
