// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "../BaseStrategySwapper.sol";

import "interfaces/keeper/ILiquidityPoolV2.sol";

/*
    Strategy to optimize rewards for an arbitrary keeper pool.
*/
contract StrategyKeeperLpOptimizer is BaseStrategyMultiSwapper {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    // TODO: Decide on rewards harvesting strategy.
    // NB: Currently only the uni ROOK/ETH has any liquidity so the swap path we have to
    // take is ROOK -> WETH -> RenBTC on uni.
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // WEth token
    // NB: There is no staking of rook available.
    address public constant rook = 0xfA5047c9c78B8877af97BDcb85Db743fD7313d4a; // Rook token

    // 100% of rook rewards just go to rewards manager.
    address public badgerRewardsManager;

    event HarvestState(
        uint256 totalRook,
        uint256 toGovernance,
        uint256 toStrategist,
        uint256 toBadgerRewardsManager,
        uint256 timestamp,
        uint256 blockNumber
    );

    struct HarvestData {
        uint256 totalRook;
        uint256 toGovernance;
        uint256 toStrategist;
        uint256 toBadgerRewardsManager;
    }

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[2] memory _wantConfig,
        uint256[3] memory _feeConfig
    ) public initializer whenNotPaused {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        badgerRewardsManager = _wantConfig[1];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
    }

    /// ===== View Functions =====
    function version() external pure returns (string memory) {
        return "1.2";
    }

    function getName() external override pure returns (string memory) {
        return "StrategyKeeperLpOptimizer";
    }

    function balanceOfPool() public override view returns (uint256) {
        // No staking pool, balance consists entirely of idle want.
        return 0;
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](2);
        protectedTokens[0] = want;
        protectedTokens[1] = rook;
        return protectedTokens;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(address(rook) != _asset, "rook");
    }

    function _deposit(uint256 _want) internal override {
        // no-op, want stays idle.
    }

    /// No strategy positions. Transfer non-core tokens to controller rewards.
    function _withdrawAll() internal override {
        // Collect all rewards and transfer to controller.
        uint256 _rook = IERC20Upgradeable(rook).balanceOf(address(this));
        IERC20Upgradeable(rook).safeTransfer(IController(controller).rewards(), _rook);
    }

    /// @dev Withdraw want from staking rewards, using earnings first
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        // no-op, base strategy  handles transfer of idle want.
        return 0;
    }

    // NB: Actual claiming of rewards happens off chain but ROOK rewards end up
    // in the strategy and still need to be harvested.
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        // All rook is profit. Actual claiming of rewards happens off chain>
        harvestData.totalRook = IERC20Upgradeable(rook).balanceOf(address(this));
        harvestData.toStrategist = _processFee(rook, harvestData.totalRook, performanceFeeStrategist, strategist);
        harvestData.toGovernance = _processFee(rook, harvestData.totalRook, performanceFeeGovernance, IController(controller).rewards());
        // Transfer remainder to badger rewards manager.
        harvestData.toBadgerRewardsManager = IERC20Upgradeable(rook).balanceOf(address(this));

        emit HarvestState(
            harvestData.totalRook,
            harvestData.toStrategist,
            harvestData.toGovernance,
            harvestData.toBadgerRewardsManager,
            block.timestamp,
            block.number
        );

        // We never increase underlying position.
        emit Harvest(0, block.number);

        return harvestData;
    }
}
