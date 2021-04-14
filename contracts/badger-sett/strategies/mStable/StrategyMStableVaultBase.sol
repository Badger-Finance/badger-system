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
        want = _wantConfig[0]; // mAsset
        vault = _wantConfig[1];
        voterProxy = _wantConfig[2];
        lpComponent = _wantConfig[3];
        badgerTree = _wantConfig[4];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
        govMta = _feeConfig[3]; // 1000

        _safeApproveHelper(lpComponent, want, type(uint256).max);
    }

    /// ===== View Functions =====

    function getName() external override pure returns (string memory) {
        return "StrategyMStableVault";
    }

    function version() external pure returns (string memory) {
        return "1.0";
    }

    function balanceOfPool() public override view returns (uint256) {
        return IMStableBoostedVault(vault).rawBalanceOf(voterProxy);
    }

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
        IERC20Upgradeable(want).transfer(voterProxy, _want);
        IMStableVoterProxy(voterProxy).deposit(_want);
    }

    function _withdrawAll() internal override {
        IMStableVoterProxy(voterProxy).withdrawAll();
    }

    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        IMStableVoterProxy(voterProxy).withdrawSome(_amount);
        return _amount;
    }

    /// @notice Harvest from strategy mechanics, realizing increase in underlying position
    function harvest() external whenNotPaused returns (HarvestData memory) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        uint256 _wantBefore = IERC20Upgradeable(want).balanceOf(address(this));

        // Harvest from Vault
        uint256 _mtaVested = IMStableVoterProxy(voterProxy).claim();
        harvestData.mtaTotal = IERC20Upgradeable(mta).balanceOf(address(this));

        // Step 1: Send a percentage of MTA back to voterProxy for reinvestment
        harvestData.mtaSentToVoterProxy = harvestData.mtaTotal.mul(govMta).div(MAX_FEE);
        IERC20Upgradeable(mta).safeTransfer(voterProxy, harvestData.mtaSentToVoterProxy);

        // Step 2: send Post-vesting rewards to BadgerTree
        harvestData.mtaPostVesting = _mtaVested.mul(MAX_FEE.sub(govMTA)).div(MAX_FEE);
        (harvestData.mtaFees[0], harvestData.mtaFees[1]) = _processPerformanceFees(mta, harvestData.mtaPostVesting);
        harvestData.mtaPostVestingSentToBadgerTree = harvestData.mtaPostVesting.sub(harvestData.mtaFees[0]).sub(harvestData.mtaFees[1]);
        IERC20Upgradeable(mta).safeTransfer(badgerTree, harvestData.mtaPostVestingSentToBadgerTree);

        // Step 3: convert remainder to LP and reinvest
        uint256 _mta = IERC20Upgradeable(mta).balanceOf(address(this));
        harvestData.mtaRecycledToWant = _mta;
        if (harvestData.mtaRecycledToWant > 0) {
            address[] memory path = new address[](3);
            path[0] = mta;
            path[1] = weth;
            path[2] = lpComponent;
            _swap(mta, harvestData.mtaRecycledToWant, path);
        }
        harvestData.lpComponentDeposited = IERC20Upgradeable(lpComponent).balanceOf(address(this));
        if (harvestData.lpComponentDeposited > 0) {
            _mintWant(lpComponent, harvestData.lpComponentDeposited);
        }
        // Take fees from LP increase, and deposit remaining into Vault
        harvestData.wantProcessed = IERC20Upgradeable(want).balanceOf(address(this));
        if (harvestData.wantProcessed > 0) {
            (harvestData.wantFees[0], harvestData.wantFees[1]) = _processPerformanceFees(want, harvestData.wantProcessed);

            // Deposit remaining want into Vault
            harvestData.wantDeposited = IERC20Upgradeable(want).balanceOf(address(this));

            if (harvestData.wantDeposited > 0) {
                _deposit(harvestData.wantDeposited);
            }
        }

        // TODO - ensure all these are set accurately
        emit MStableHarvest(
            harvestData.mtaTotal, // Total units farmed from vault (immediate + vested), before fees
            harvestData.mtaSentToVoterProxy, // % sent back to VoterProxy to be reinvested
            harvestData.mtaRecycledToWant, // mta recycled back to want for compounding
            harvestData.lpComponentDeposited,
            harvestData.wantProcessed,
            harvestData.wantFees,
            harvestData.wantDeposited,
            harvestData.mtaPostVesting, // mta earned post vesting, after deducting voterProxy fee
            harvestData.mtaFees,
            harvestData.mtaPostVestingSentToBadgerTree
        );
        emit Harvest(harvestData.wantProcessed.sub(_wantBefore), block.number);

        return harvestData;
    }

    /// ===== Internal Helper Functions =====

    function _mintWant(address _input, uint256 _amount) internal virtual {
        IMStableAsset(want).mint(_input, _amount, _amount.mul(80).div(100), address(this));
    }

    function _processPerformanceFees(address _token, uint256 _amount)
        internal
        returns (uint256 governancePerformanceFee, uint256 strategistPerformanceFee)
    {
        governancePerformanceFee = _processFee(_token, _amount, performanceFeeGovernance, IController(controller).rewards());

        strategistPerformanceFee = _processFee(_token, _amount, performanceFeeStrategist, strategist);
    }
}
