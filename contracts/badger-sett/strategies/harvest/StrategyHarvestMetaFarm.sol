// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/MathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "interfaces/harvest/IDepositHelper.sol";
import "interfaces/harvest/IHarvestVault.sol";
import "interfaces/harvest/IRewardPool.sol";

import "interfaces/uniswap/IUniswapRouterV2.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";
import "../BaseStrategy.sol";

contract StrategyHarvestMetaFarm is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    address public harvestVault;
    address public vaultFarm;
    address public metaFarm;
    address public badgerTree;

    /// @notice FARM performance fees take a cut of outgoing farm
    uint256 public farmPerformanceFeeGovernance;
    uint256 public farmPerformanceFeeStrategist;

    uint256 public lastHarvested;

    address public constant farm = 0xa0246c9032bC3A600820415aE600c6388619A14D; // FARM Token
    address public constant depositHelper = 0xF8ce90c2710713552fb564869694B2505Bfc0846; // Harvest deposit helper
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token

    event Tend(uint256 farmTended);

    event FarmHarvest(
        uint256 totalFarmHarvested,
        uint256 farmToRewards,
        uint256 governancePerformanceFee,
        uint256 strategistPerformanceFee,
        uint256 timestamp,
        uint256 blockNumber
    );

    struct HarvestData {
        uint256 totalFarmHarvested;
        uint256 farmToRewards;
        uint256 governancePerformanceFee;
        uint256 strategistPerformanceFee;
    }

    struct TendData {
        uint256 farmTended;
    }

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[5] memory _wantConfig,
        uint256[3] memory _feeConfig
    ) public initializer {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        want = _wantConfig[0];
        harvestVault = _wantConfig[1];
        vaultFarm = _wantConfig[2];
        metaFarm = _wantConfig[3];
        badgerTree = _wantConfig[4];

        farmPerformanceFeeGovernance = _feeConfig[0];
        farmPerformanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        IERC20Upgradeable(want).safeApprove(harvestVault, type(uint256).max);
        IERC20Upgradeable(want).safeApprove(depositHelper, type(uint256).max);
        IERC20Upgradeable(harvestVault).safeApprove(vaultFarm, type(uint256).max);
        IERC20Upgradeable(farm).safeApprove(metaFarm, type(uint256).max);

        // Trust Uniswap with unlimited approval for swapping efficiency
        IERC20Upgradeable(farm).safeApprove(uniswap, type(uint256).max);
    }

    /// ===== View Functions =====

    function getName() external override pure returns (string memory) {
        return "StrategyHarvestMetaFarm";
    }

    /// @dev Realizable balance of our shares
    /// TODO: If this is wrong, it will overvalue our shares (we will get LESS for each share we redeem) This means the user will lose out.
    function balanceOfPool() public override view returns (uint256) {
        uint256 vaultShares = IHarvestVault(harvestVault).balanceOf(address(this));
        uint256 farmShares = IRewardPool(vaultFarm).balanceOf(address(this));

        return _fromHarvestVaultTokens(vaultShares.add(farmShares));
    }

    function isTendable() public override view returns (bool) {
        return true;
    }

    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](3);
        protectedTokens[0] = want;
        protectedTokens[1] = farm;
        protectedTokens[2] = harvestVault;
        return protectedTokens;
    }

    /// ===== Permissioned Actions: Governance =====
    function setFarmPerformanceFeeGovernance(uint256 _fee) external {
        _onlyGovernance();
        farmPerformanceFeeGovernance = _fee;
    }

    function setFarmPerformanceFeeStrategist(uint256 _fee) external {
        _onlyGovernance();
        farmPerformanceFeeStrategist = _fee;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(address(farm) != _asset, "farm");
        require(address(harvestVault) != _asset, "harvestVault");
    }

    function _deposit(uint256 _want) internal override {
        // Deposit want into Harvest vault via deposit helper

        uint256[] memory amounts = new uint256[](1);
        address[] memory tokens = new address[](1);

        amounts[0] = _want;
        tokens[0] = harvestVault;

        IDepositHelper(depositHelper).depositAll(amounts, tokens);
    }

    /// @notice Deposit other tokens
    function _postDeposit() internal override {
        uint256 _fWant = IERC20Upgradeable(harvestVault).balanceOf(address(this));

        // Deposit fWant -> Staking
        if (_fWant > 0) {
            IRewardPool(vaultFarm).stake(_fWant);
        }
    }

    function _withdrawAll() internal override {
        uint256 _stakedFarm = IRewardPool(metaFarm).balanceOf(address(this));

        if (_stakedFarm > 0) {
            IRewardPool(metaFarm).exit();
        }

        uint256 _stakedShares = IRewardPool(vaultFarm).balanceOf(address(this));

        if (_stakedShares > 0) {
            IRewardPool(vaultFarm).exit();
        }

        uint256 _fShares = IHarvestVault(harvestVault).balanceOf(address(this));

        if (_fShares > 0) {
            IHarvestVault(harvestVault).withdraw(_fShares);
        }

        // Send any unproessed FARM to rewards
        uint256 _farm = IERC20Upgradeable(farm).balanceOf(address(this));

        if (_farm > 0) {
            IERC20Upgradeable(farm).transfer(IController(controller).rewards(), _farm);
        }
    }

    /// @dev Withdraw vaultTokens from vaultFarm first, followed by harvestVault
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        uint256 _preWant = IERC20Upgradeable(want).balanceOf(address(this));

        uint256 _toWithdraw = _amount;

        uint256 _wrappedTotal = IRewardPool(vaultFarm).balanceOf(address(this));
        uint256 _underlyingTotal = IHarvestVault(harvestVault).balanceOf(address(this));

        if (_wrappedTotal > 0) {
            uint256 _wrappedToWithdraw = MathUpgradeable.min(_wrappedTotal, _amount);
            IRewardPool(vaultFarm).withdraw(_wrappedToWithdraw);

            _toWithdraw = _toWithdraw.sub(_wrappedToWithdraw);
        }

        if (_toWithdraw > 0 && _underlyingTotal > 0) {
            IHarvestVault(harvestVault).withdraw(_toHarvestVaultTokens(_toWithdraw));
        }

        uint256 _postWant = IERC20Upgradeable(want).balanceOf(address(this));

        // Return the actual amount withdrawn if less than requested
        return MathUpgradeable.min(_postWant.sub(_preWant), _amount);
    }

    /// @notice Harvest from strategy mechanics, realizing increase in underlying position
    /// @notice For this strategy, harvest rewards are sent to rewards tree for distribution rather than converted to underlying
    /// @notice Any APY calculation must consider expected results from harvesting
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        // Unstake all FARM from metaFarm, harvesting rewards in the process
        uint256 _farmStaked = IRewardPool(metaFarm).balanceOf(address(this));

        if (_farmStaked > 0) {
            IRewardPool(metaFarm).exit();
        }

        // Harvest rewards from vaultFarm
        IRewardPool(vaultFarm).getReward();

        harvestData.totalFarmHarvested = IERC20Upgradeable(farm).balanceOf(address(this));

        // Take strategist fees on FARM
        (harvestData.governancePerformanceFee, harvestData.strategistPerformanceFee) = _processPerformanceFees(harvestData.totalFarmHarvested);

        // Distribute remaining FARM rewards to rewardsTree
        harvestData.farmToRewards = IERC20Upgradeable(farm).balanceOf(address(this));
        IERC20Upgradeable(farm).transfer(badgerTree, harvestData.farmToRewards);

        lastHarvested = now;

        emit Harvest(0, block.number);
        emit FarmHarvest(
            harvestData.totalFarmHarvested,
            harvestData.farmToRewards,
            harvestData.governancePerformanceFee,
            harvestData.strategistPerformanceFee,
            now,
            block.number
        );

        return harvestData;
    }

    /// @notice 'Recycle' FARM gained from staking into profit sharing pool for increased APY
    /// @notice Any excess FARM sitting in the Strategy will be staked as well
    function tend() external whenNotPaused returns (TendData memory) {
        _onlyAuthorizedActors();

        TendData memory tendData;

        // No need to check for rewards balance: If we have no rewards available to harvest, will simply do nothing besides emit an event.
        IRewardPool(metaFarm).getReward();
        IRewardPool(vaultFarm).getReward();

        tendData.farmTended = IERC20Upgradeable(farm).balanceOf(address(this));

        // Deposit gathered FARM into profit sharing
        if (tendData.farmTended > 0) {
            IRewardPool(metaFarm).stake(tendData.farmTended);
        }

        emit Tend(tendData.farmTended);
        return tendData;
    }

    /// ===== Internal Helper Functions =====

    function _processPerformanceFees(uint256 _amount) internal returns (uint256 governancePerformanceFee, uint256 strategistPerformanceFee) {
        governancePerformanceFee = _processFee(farm, _amount, farmPerformanceFeeGovernance, IController(controller).rewards());
        strategistPerformanceFee = _processFee(farm, _amount, farmPerformanceFeeStrategist, strategist);
        return (governancePerformanceFee, strategistPerformanceFee);
    }

    /// @dev Convert underlying value into corresponding number of harvest vault shares
    function _toHarvestVaultTokens(uint256 amount) internal view returns (uint256) {
        uint256 ppfs = IHarvestVault(harvestVault).getPricePerFullShare();
        uint256 unit = IHarvestVault(harvestVault).underlyingUnit();
        return amount.mul(unit).div(ppfs);
    }

    function _fromHarvestVaultTokens(uint256 amount) internal view returns (uint256) {
        uint256 ppfs = IHarvestVault(harvestVault).getPricePerFullShare();
        uint256 unit = IHarvestVault(harvestVault).underlyingUnit();
        return amount.mul(ppfs).div(unit);
    }
}
