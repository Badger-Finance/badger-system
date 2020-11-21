// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

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
    address public rewardsEscrow;

    /// @notice FARM performance fees take a cut of outgoing farm
    uint256 public farmPerformanceFeeGovernance;
    uint256 public farmPerformanceFeeStrategist;

    uint256 public lastHarvested;

    address public constant farm = 0xa0246c9032bC3A600820415aE600c6388619A14D; // FARM Token
    address public constant depositHelper = 0xF8ce90c2710713552fb564869694B2505Bfc0846; // Harvest deposit helper
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token

    event Tend(uint256 tended);

    event FarmHarvest(
        uint256 harvested,
        uint256 transferred,
        uint256 governancePerformanceFee,
        uint256 strategistPerformanceFee,
        uint256 timestamp,
        uint256 blockNumber
    );

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
        rewardsEscrow = _wantConfig[4];

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
        IRewardPool(vaultFarm).exit();
        IHarvestVault(harvestVault).withdrawAll();
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
    function harvest() external override whenNotPaused {
        _onlyAuthorizedActors();

        uint256 _preFarm = IERC20Upgradeable(farm).balanceOf(address(this));
        IRewardPool(metaFarm).exit();
        IRewardPool(vaultFarm).getReward();
        uint256 _postFarm = IERC20Upgradeable(farm).balanceOf(address(this));

        uint256 _governanceFee = _processFee(farm, _postFarm, farmPerformanceFeeGovernance, governance);
        uint256 _strategistFee = _processFee(farm, _postFarm, farmPerformanceFeeStrategist, strategist);

        uint256 _postFeeFarm = IERC20Upgradeable(farm).balanceOf(address(this));
        IERC20Upgradeable(farm).transfer(rewardsEscrow, _postFeeFarm);

        lastHarvested = now;

        emit FarmHarvest(_postFarm.sub(_preFarm), _postFeeFarm, _governanceFee, _strategistFee, now, block.number);
    }

    /// @notice 'Recycle' FARM gained from staking into profit sharing pool for increased APY
    /// @notice Any excess FARM sitting in the Strategy will be staked as well
    function tend() external {
        _onlyAuthorizedActors();

        uint256 _preFarm = IERC20Upgradeable(farm).balanceOf(address(this));

        // No need to check for rewards balance: If we have no rewards available to harvest, will simply do nothing besides emit an event.
        IRewardPool(metaFarm).getReward();
        IRewardPool(vaultFarm).getReward();

        uint256 _postFarm = IERC20Upgradeable(farm).balanceOf(address(this));

        // Deposit gathered FARM into profit sharing
        if (_postFarm > 0) {
            IRewardPool(metaFarm).stake(_postFarm);
        }

        emit Tend(_postFarm.sub(_preFarm));
    }

    /// ===== Internal Helper Functions =====

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
