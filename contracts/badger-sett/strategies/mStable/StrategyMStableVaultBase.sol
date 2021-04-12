// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "interfaces/mStable/IMStableAsset.sol";
import "interfaces/mStable/IMStableBoostedVault.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "./IMStableVoterProxy.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";
import "../BaseStrategy.sol";

contract StrategyMStableVaultBase is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    // TODO - remove config if unused
    address public vault; // i.e. imBTC BoostedSavingsVault
    address public voterProxy; // MStableVoterProxy
    address public mAsset; // i.e. imBTC, fPmBTC/HBTC
    address public lpComponent; // i.e. wBTC, sBTC, renBTC, HBTC

    address public constant mta = 0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2; // MTA token
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token, used for mta -> weth -> lpComponent route
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // Wbtc Token

    uint256 public govMta;
    address public badgerTree;

    // TODO - change output
    event MStableHarvest(
        uint256 mtaHarvested,
        uint256 mtaVested,
        uint256 govMta,
        uint256 toGovernance,
        uint256 toStrategist,
        uint256 toBadgerTree
    );

    // TODO - change output
    struct HarvestData {
        uint256 mtaHarvested;
        uint256 mtaVested;
        uint256 govMta;
        uint256 toGovernance;
        uint256 toStrategist;
        uint256 toBadgerTree;
    }

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[5] memory _wantConfig,
        uint256[4] memory _feeConfig
    ) public initializer {
        __BaseStrategy_init(_governance, _strategist, _controller, _keeper, _guardian);

        // TODO - clean import lists based on strategy chosen
        // TODO - remove config if unused
        want = _wantConfig[0];
        vault = _wantConfig[1];
        mAsset = _wantConfig[2];
        lpComponent = _wantConfig[3];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
        govMta = _feeConfig[3]; // 1000

        IERC20Upgradeable(want).safeApprove(gauge, type(uint256).max);
    }

    /// ===== View Functions =====

    function getName() external override pure returns (string memory) {
        return "StrategyMStableVault";
    }

    function version() external pure returns (string memory) {
        return "1.0";
    }

    function balanceOfPool() public override view returns (uint256) {
        // return ICurveGauge(gauge).balanceOf(address(this));
        // TODO - read directly, or call the voterProxy?
        return IMStableBoostedVault(vault).rawBalanceOf(voterProxy);
    }

    // TODO - verify purpose of this fn
    function getProtectedTokens() external override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](3);
        protectedTokens[0] = want;
        protectedTokens[1] = lpComponent;
        protectedTokens[2] = mta;
        return protectedTokens;
    }

    /// ===== Permissioned Actions: Governance =====

    function setgovMta(uint256 _govMta) external {
        _onlyGovernance();
        govMta = _govMta;
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(lpComponent != _asset, "lpComponent");
        require(mta != _asset, "mta");
    }

    function _deposit(uint256 _want) internal override {
        // ICurveGauge(gauge).deposit(_want);
        // TODO - verify deposit via voterProxy
        IERC20Upgradeable(want).transfer(voterProxy, _want);
        IMStableVoterProxy(voterProxy).deposit(_want);
    }

    function _withdrawAll() internal override {
        // ICurveGauge(gauge).withdraw(ICurveGauge(gauge).balanceOf(address(this)));
        IMStableVoterProxy(voterProxy).withdrawAll();
    }

    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        // ICurveGauge(gauge).withdraw(_amount);
        IMStableVoterProxy(voterProxy).withdrawSome(_amount);
        return _amount;
    }

    /// @notice Harvest from strategy mechanics, realizing increase in underlying position
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _beforeMta = IERC20Upgradeable(mta).balanceOf(address(this));

        // Harvest from Gauge
        uint256 _vestedMta = IMStableVoterProxy(voterProxy).claim();
        uint256 _afterMta = IERC20Upgradeable(mta).balanceOf(address(this));

        uint256 _immediateUnlock = _afterMta.sub(_vestedMta).sub(_beforeMta);

        // mStable: At this point, we have access to both immediately unlocked MTA, and those
        // that have undergone vesting. We should find distribution methods for them that:
        //   a) produce good incentives
        //   b) do not increase gas usage too much
        //   c) does not add insane amounts of complexity
        // 1) Ideal:
        //  Immediate - Sell for lpComponent and mint mBTC (vault compounding)
        //  Post-vesting - MTA distributed through BadgerTree
        // 2) Both options same:
        //  Immediate - Sell for lpComponent and mint mBTC
        //  Post-vesting - Sell for lpComponent and distribute through BadgerTree (these can't be reinvested because they are earned 6m later)
        // 3) Lowest gas cost/complexity:
        //  Immediate - Distribute through BadgerTree
        //  Post-vesting - Distribute through BadgerTree
        // I believe option 2 makes the most sense - the additional complexity adds up v quickly (
        // i.e. ) and
        // calling harvest daily at an extra 1-200k gas eats away at the rationale for doing so.

        // TODO - recycle into geyser?

        harvestData.mtaHarvested = _immediateUnlock;
        harvestData.mtaVested = _vestedMta;
        uint256 _mta = _afterMta;

        // Send MTA back to voterProxy for reinvestment
        harvestData.govMta = _mta.mul(govMta).div(MAX_FEE);
        IERC20Upgradeable(mta).safeTransfer(voterProxy, harvestData.govMta);

        // Take performance fees from remainder
        (harvestData.toGovernance, harvestData.toStrategist) = _processPerformanceFees(_mta.sub(harvestData.govMta));

        // Transfer remainder to Tree
        harvestData.toBadgerTree = IERC20Upgradeable(mta).balanceOf(address(this));
        IERC20Upgradeable(mta).safeTransfer(badgerTree, harvestData.toBadgerTree);

        emit CurveHarvest(
            harvestData.mtaHarvested,
            harvestData.mtaVested,
            harvestData.govMta,
            harvestData.toGovernance,
            harvestData.toStrategist,
            harvestData.toBadgerTree
        );
        // No increase in underlying position
        emit Harvest(0, block.number);

        return harvestData;
    }

    /// ===== Internal Helper Functions =====

    function _processPerformanceFees(uint256 _amount) internal returns (uint256 governancePerformanceFee, uint256 strategistPerformanceFee) {
        governancePerformanceFee = _processFee(mta, _amount, performanceFeeGovernance, IController(controller).rewards());

        strategistPerformanceFee = _processFee(mta, _amount, performanceFeeStrategist, strategist);
    }
}
