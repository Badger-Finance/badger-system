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

/*
    Strategy to compound badger rewards
    - Deposit Badger into the vault to receive more from a special rewards pool
*/
contract StrategyBadgerRewards is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public geyser;

    struct HarvestData {
        uint256 wantIncrease;
        uint256 wantDeposited;
    }

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
        geyser = _wantConfig[1];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
    }

    /// ===== View Functions =====
    function getName() external override pure returns (string memory) {
        return "StrategyBadgerRewards";
    }

    function balanceOfPool() public override view returns (uint256) {
        return IStakingRewards(geyser).balanceOf(address(this));
    }

    function getProtectedTokens() external view override returns (address[] memory) {
        address[] memory protectedTokens = new address[](2);
        protectedTokens[0] = want;
        protectedTokens[1] = geyser;
        return protectedTokens;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(address(geyser) != _asset, "geyser");
    }

    /// @notice Deposit want into a special rewards contract
    function _deposit(uint256 _want) internal override {
        _safeApproveHelper(want, geyser, _want);
        IStakingRewards(geyser).stake(_want);
    }

    /// @dev Exit staking rewards
    /// @dev All claimed rewards are in want so no further actions needed
    function _withdrawAll() internal override {
        IStakingRewards(geyser).exit();
    }

    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        // Use idle Badger if available
        uint256 _before = IERC20Upgradeable(want).balanceOf(address(this));

        if (_before >= _amount) {
            return _amount;
        }

        // Unstake the remainder from StakingRewards
        uint256 _remainder = _amount.sub(_before);
        IStakingRewards(geyser).withdraw(_remainder);

        return _amount;
    }

    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _before = IERC20Upgradeable(want).balanceOf(address(this));

        IStakingRewards(geyser).getReward();

        harvestData.wantDeposited = IERC20Upgradeable(want).balanceOf(address(this));
        if (harvestData.wantDeposited > 0) {
            _deposit(harvestData.wantDeposited);
        }

        harvestData.wantIncrease = harvestData.wantDeposited.sub(_before);

        emit Harvest(harvestData.wantIncrease, block.number);

        return harvestData;
    }
}
