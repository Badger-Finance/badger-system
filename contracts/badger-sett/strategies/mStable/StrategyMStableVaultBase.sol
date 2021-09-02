// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "interfaces/mStable/IMStableAsset.sol";
import "interfaces/mStable/IMStableBoostedVault.sol";
import "interfaces/mStable/IMStableVoterProxy.sol";

import "interfaces/badger/IController.sol";
import "../BaseStrategySwapper.sol";

/// @title  StrategyMStableVaultBase
/// @author mStable
/// @notice Base Strategy for all mStable Vaults.
/// @dev    mStable has yield bearing LP tokens and gives MTA rewards via mStable Vaults. 33% of
///         rewards are unlocked immediately and 67% are vested over 6 months (on chain). These MTA rewards
///         can be boosted up to 3x by staking in mStable MTA Staking contract (this boost applies to all vaults).
///         This MTA staking contract also gives out MTA.
///         mStable strategies follow the same flow in which the 33% immediate unlock is converted back into the LP
///         token, and re-deposited into the Vault, making it a compounding interest. The 67% unlock is distributed
///         in MTA terms via the BadgerTree (awarding to users active 6 months ago). Before these distributions, %
///         of all MTA earned is taken and staked to boost the rewards and earn more MTA yield.
///         Deposits to the mStable vaults go via the VoterProxy. This proxy:
///          - manages the lock in the MTA staking contract
///          - earns APY on staked MTA
///          - boost rewards in vault deposits
///          - vote on proposals on the mStableDAO (after the next version of staking comes that allows vote delegation)
abstract contract StrategyMStableVaultBase is BaseStrategyMultiSwapper {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using SafeMathUpgradeable for uint256;

    address public vault; // i.e. imBTC BoostedSavingsVault
    address public voterProxy; // MStableVoterProxy
    address public lpComponent; // i.e. wBTC, sBTC, renBTC, HBTC
    address public badgerTree; // redistributor address

    address public constant mta = 0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2; // MTA token
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // Weth Token, used for mta -> weth -> lpComponent route
    address public constant mBTC = 0x945Facb997494CC2570096c74b5F66A3507330a1; // mBTC token

    uint256 public govMta; // % of MTA returned to VoterProxy

    event GovMtaSet(uint256 govMta);

    event TreeDistribution(address indexed token, uint256 amount, uint256 indexed blockNumber, uint256 timestamp);

    event MStableHarvest(
        uint256 mtaTotal,
        uint256 mtaSentToVoterProxy,
        uint256 mtaRecycledToWant,
        uint256 lpComponentPurchased,
        uint256 wantProcessed,
        uint256[2] wantFees,
        uint256 wantDeposited,
        uint256 mtaPostVesting,
        uint256[2] mtaFees,
        uint256 mtaPostVestingSentToBadgerTree
    );

    struct HarvestData {
        uint256 mtaTotal; // Total units farmed from vault (immediate + vested), before fees
        // mtaTotal == mtaSentToVoterProxy + mtaRecycledToWant + mtaPostVesting
        uint256 mtaSentToVoterProxy; // Units sent back to VoterProxy to be reinvested
        uint256 mtaRecycledToWant; // MTA recycled back to want for compounding, after deducting voterProxy
        uint256 lpComponentPurchased; // LP components purchased from MTA
        uint256 wantProcessed; // Output from mint
        uint256[2] wantFees; // Fees taken from wantProcessed
        uint256 wantDeposited; // Units deposited back into vault
        uint256 mtaPostVesting; // MTA earned post vesting, after deducting voterProxy
        uint256[2] mtaFees; // Fees taken from the post-vesting MTA
        uint256 mtaPostVestingSentToBadgerTree; // Post-vesting MTA units sent to BadgerTree for distribution
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

        want = _wantConfig[0];
        vault = _wantConfig[1];
        voterProxy = _wantConfig[2];
        lpComponent = _wantConfig[3];
        badgerTree = _wantConfig[4];

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];
        govMta = _feeConfig[3];

        // For FpMbtcHbtc just approve lp to want
        _safeApproveHelper(lpComponent, want, type(uint256).max);
        // For imBTC, approve lp to mBTC, then mBTC to want (imBTC)
        _safeApproveHelper(lpComponent, mBTC, type(uint256).max);
        _safeApproveHelper(mBTC, want, type(uint256).max);
    }

    /// ===== View Functions =====

    function getName() external override pure returns (string memory) {
        return "StrategyMStableVault";
    }

    function version() external pure returns (string memory) {
        return "1.0";
    }

    /// @dev Reads the balance of VoterProxy directly from the vault rather than calling the VoterProxy
    function balanceOfPool() public override view returns (uint256) {
        // rawBalanceOf returns units of want owned by voterProxy in vault
        return IMStableBoostedVault(vault).rawBalanceOf(voterProxy);
    }

    function getProtectedTokens() public override view returns (address[] memory) {
        address[] memory protectedTokens = new address[](3);
        protectedTokens[0] = want;
        protectedTokens[1] = lpComponent;
        protectedTokens[2] = mta;
        return protectedTokens;
    }

    /// ===== Permissioned Actions: Governance =====

    /// @notice Sets the % of accrued MTA rewards that are reinvested to VoterProxy
    /// @param _govMta  % of MTA to return, where 1% == 100 and 100% == 10000
    function setGovMta(uint256 _govMta) external {
        _onlyGovernance();
        require(_govMta < MAX_FEE, "Invalid rate");

        govMta = _govMta;

        emit GovMtaSet(_govMta);
    }

    /// ===== Internal Core Implementations =====

    function _onlyNotProtectedTokens(address _asset) internal override {
        require(address(want) != _asset, "want");
        require(lpComponent != _asset, "lpComponent");
        require(mta != _asset, "mta");
    }

    /// @dev Deposits an amount of want to the mStable vault via the VoterProxy
    /// @param _want Units of want to transfer to VoterProxy and deposit to the vault
    function _deposit(uint256 _want) internal override {
        IERC20Upgradeable(want).transfer(voterProxy, _want);
        IMStableVoterProxy(voterProxy).deposit(_want);
    }

    /// @dev Withdraws all units of want from the vault via the VoterProxy
    function _withdrawAll() internal override {
        IMStableVoterProxy(voterProxy).withdrawAll(want);
    }

    /// @dev Withdraws a certain number of want units from the vault via the VoterProxy
    /// @param _amount Units of want to withdraw
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        IMStableVoterProxy(voterProxy).withdrawSome(want, _amount);
        return _amount;
    }

    /// @notice Harvest from strategy mechanics, realizing increase in underlying position
    function harvest() external whenNotPaused returns (uint256) {
        _onlyAuthorizedActors();

        HarvestData memory harvestData;

        // Step 1: Claim new rewards from the vault via VoterProxy
        uint256 _wantBefore = IERC20Upgradeable(want).balanceOf(address(this));
        // _mtaVested shows the units of MTA that have been claimed, after passing their 6 month vesting period
        (, uint256 _mtaVested) = IMStableVoterProxy(voterProxy).claim();
        // Any MTA in this contract is assumed to be freshly claimed
        harvestData.mtaTotal = IERC20Upgradeable(mta).balanceOf(address(this));

        // Step 2: Send a percentage of all MTA back to voterProxy for reinvestment
        // e.g. 9e18 * 1000 / 10000 = 9e17
        harvestData.mtaSentToVoterProxy = harvestData.mtaTotal.mul(govMta).div(MAX_FEE);
        IERC20Upgradeable(mta).safeTransfer(voterProxy, harvestData.mtaSentToVoterProxy);

        // Step 3: Send Post-vesting rewards to BadgerTree
        // mtaPostVesting = vestedMTA - govFee = vestedMTA * (1-govFee) / maxFee
        // e.g. 6e18 * 9000 / 10000 = 54e16
        harvestData.mtaPostVesting = _mtaVested.mul(MAX_FEE.sub(govMta)).div(MAX_FEE);
        if (harvestData.mtaPostVesting > 0) {
            (harvestData.mtaFees[0], harvestData.mtaFees[1]) = _processPerformanceFees(mta, harvestData.mtaPostVesting);
            harvestData.mtaPostVestingSentToBadgerTree = harvestData.mtaPostVesting.sub(harvestData.mtaFees[0]).sub(harvestData.mtaFees[1]);
            IERC20Upgradeable(mta).safeTransfer(badgerTree, harvestData.mtaPostVestingSentToBadgerTree);
            emit TreeDistribution(mta, harvestData.mtaPostVestingSentToBadgerTree, block.number, block.timestamp);
        }

        // Step 4: convert remainder to LP and reinvest
        // Immediately unlocked rewards = mtaTotal - govFee - mtaPostVesting
        uint256 _mta = IERC20Upgradeable(mta).balanceOf(address(this));
        harvestData.mtaRecycledToWant = _mta;
        //      4.1: Convert MTA to LPComponent via Uniswap MTA -> WETH -> LPComponent
        if (harvestData.mtaRecycledToWant > 0) {
            address[] memory path = new address[](3);
            path[0] = mta;
            path[1] = weth;
            path[2] = lpComponent;
            _swap(mta, harvestData.mtaRecycledToWant, path);
        }
        //      4.2: Mint mStable Asset (want) from the lpComponent
        harvestData.lpComponentPurchased = IERC20Upgradeable(lpComponent).balanceOf(address(this));
        if (harvestData.lpComponentPurchased > 0) {
            _mintWant(lpComponent, harvestData.lpComponentPurchased);
        }
        //      4.3: Take fees from LP increase, and deposit remaining into Vault via VoterProxy
        harvestData.wantProcessed = IERC20Upgradeable(want).balanceOf(address(this));
        if (harvestData.wantProcessed > 0) {
            (harvestData.wantFees[0], harvestData.wantFees[1]) = _processPerformanceFees(want, harvestData.wantProcessed);

            // Deposit remaining want into Vault
            harvestData.wantDeposited = IERC20Upgradeable(want).balanceOf(address(this));

            if (harvestData.wantDeposited > 0) {
                _deposit(harvestData.wantDeposited);
            }
        }

        emit MStableHarvest(
            harvestData.mtaTotal, // Total units farmed from vault (immediate + vested), before fees
            // mtaTotal == mtaSentToVoterProxy + mtaRecycledToWant + mtaPostVesting
            harvestData.mtaSentToVoterProxy, // Units sent back to VoterProxy to be reinvested
            harvestData.mtaRecycledToWant, // MTA recycled back to want for compounding, after deducting voterProxy
            harvestData.lpComponentPurchased, // LP components purchased from MTA
            harvestData.wantProcessed, // Output from mint
            harvestData.wantFees, // Fees taken from wantProcessed
            harvestData.wantDeposited, // Units deposited back into vault
            harvestData.mtaPostVesting, // MTA earned post vesting, after deducting voterProxy
            harvestData.mtaFees, // Fees taken from the post-vesting MTA
            harvestData.mtaPostVestingSentToBadgerTree // Post-vesting MTA units sent to BadgerTree for distribution
        );
        emit Harvest(harvestData.wantProcessed.sub(_wantBefore), block.number);

        return harvestData.wantProcessed.sub(_wantBefore);
    }

    /// ===== Internal Helper Functions =====

    /// @dev Mints mStable Asset using a specified input and amount
    /// @param _input Address of asset to be used in the mint
    /// @param _amount Units of _input to mint with
    function _mintWant(address _input, uint256 _amount) internal virtual;

    /// @dev Processes performance fees for a particular token
    /// @param _token Address of the token to process
    /// @param _amount Total units of the asset that should be extracted from
    function _processPerformanceFees(address _token, uint256 _amount)
        internal
        returns (uint256 governancePerformanceFee, uint256 strategistPerformanceFee)
    {
        governancePerformanceFee = _processFee(_token, _amount, performanceFeeGovernance, IController(controller).rewards());

        strategistPerformanceFee = _processFee(_token, _amount, performanceFeeStrategist, strategist);
    }
}
