// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";

import "interfaces/mStable/IMStableNexus.sol";
import "interfaces/mStable/IMStableBoostedVault.sol";
import "interfaces/mStable/IMStableVotingLockup.sol";
import "interfaces/mStable/IMStableVoterProxy.sol";
import "interfaces/badger/IStrategy.sol";

import "../../SettAccessControl.sol";

/// @title  MStableVoterProxy
/// @author mStable
/// @notice VoterProxy that deposits into mStable vaults and uses MTA stake to boosts rewards.
/// @dev    Receives MTA from Strategies and Loans in order to bolster Stake. Any MTA held here is
///         assumed to be invested to staking.
///         This is a dumb contract that:
///          - Deposits and withdraws LP tokens from all mStable vaults
///          - Manages the lock in the MTA staking contract
///          - Earns APY on staked MTA and reinvests
///          - Boosts rewards in vault deposits
///          - Migrates to a new Staking contract if necessary
contract MStableVoterProxy is IMStableVoterProxy, PausableUpgradeable, SettAccessControl {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using SafeMathUpgradeable for uint256;

    mapping(address => IMStableBoostedVault) public strategyToVault; // strategy => vault
    address[] public strategies;

    address public badgerGovernance;
    IMStableNexus public nexus; // mStable Nexus maintains record of governor address
    IMStableVotingLockup public votingLockup; // Current MTA staking contract address

    mapping(address => uint256) public loans; // Outstanding loans made to this contract
    IERC20Upgradeable public constant mta = IERC20Upgradeable(0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2);

    uint256 public MAX_RATE = 10000;
    uint256 public redistributionRate;

    event LockCreated(uint256 amt, uint256 unlockTime);
    event MtaHarvested(uint256 existing, uint256 harvested, uint256 distributed, uint256 invested);
    event LockExtended(uint256 unlockTime);
    event LockExited();
    event LockChanged(address newLock);
    event RedistributionRateChanged(uint256 newRate);

    event Loaned(address creditor, uint256 amt);
    event LoanRepaid(address creditor, uint256 amt);

    event StrategyAdded(address strategy, address vault);

    function initialize(
        address _dualGovernance,
        address _badgerGovernance,
        address _strategist,
        address _keeper,
        address[2] memory _config,
        uint256[1] memory _rates
    ) public initializer {
        __Pausable_init();
        governance = _dualGovernance;
        badgerGovernance = _badgerGovernance;
        strategist = _strategist;
        keeper = _keeper;

        nexus = IMStableNexus(_config[0]);
        votingLockup = IMStableVotingLockup(_config[1]);

        redistributionRate = _rates[0];

        mta.safeApprove(address(votingLockup), type(uint256).max);
    }

    /// @dev Verifies that the caller is an active strategy and returns the address of the vault
    function _onlyActiveStrategy() internal view returns (IMStableBoostedVault vault) {
        vault = strategyToVault[msg.sender];
        require(address(vault) != address(0), "onlyStrategy");
    }

    /// @dev Callable by either the mStableDAO or the BadgerDAO signers
    function _onlyGovernors() internal view {
        require(msg.sender == governance || msg.sender == nexus.governor(), "onlyGovernors");
    }

    /// @dev Callable by either the mStableDAO or the BadgerDAO signers
    function _onlyHarvesters() internal view {
        require(msg.sender == governance || msg.sender == nexus.governor() || msg.sender == keeper, "onlyHarvesters");
    }

    /***************************************
                    VOTINGLOCK
    ****************************************/

    /// @dev Creates a lock in the mStable MTA staking contract, using the mta balance of
    /// this contract, and unlocking at the specified unlock time
    /// @param _unlockTime Time at which the stake will unlock
    function createLock(uint256 _unlockTime) external override {
        _onlyGovernance();

        uint256 bal = mta.balanceOf(address(this));
        votingLockup.createLock(bal, _unlockTime);

        emit LockCreated(bal, _unlockTime);
    }

    /// @dev Claims MTA rewards from Staking, distributes a percentage proportionately to all
    /// active strategies, and reinvests the remainder back into the staking contract.
    /// Also picks up any MTA that was transferred here FROM strategies, and adds this to the lock.
    /// Callable by either mStable or Badger DAO multisigs, or keeper.
    function harvestMta() external override {
        _onlyHarvesters();

        // balBefore = any MTA that was transferred here as a govMTA % from the stratgies
        uint256 balBefore = mta.balanceOf(address(this));
        votingLockup.claimReward();
        uint256 balAfter = mta.balanceOf(address(this));
        // e.g. (2e18 - 1e18) * 1000 / 10000;
        uint256 redistribute = balAfter.sub(balBefore).mul(redistributionRate).div(MAX_RATE);
        // Redistribute a % of the revenue from staking back to the strategies
        if (redistribute > 0) {
            uint256 len = strategies.length;
            for (uint256 i = 0; i < len; i++) {
                mta.safeTransfer(strategies[i], redistribute.div(len));
            }
        }
        // Increase that lock
        votingLockup.increaseLockAmount(balAfter.sub(redistribute));

        emit MtaHarvested(balBefore, balAfter.sub(balBefore), redistribute, balAfter.sub(redistribute));
    }

    /// @dev Simply extends the lock period in staking
    /// @param _unlockTime New time at which the stake will unlock
    function extendLock(uint256 _unlockTime) external override {
        _onlyGovernance();

        votingLockup.increaseLockLength(_unlockTime);

        emit LockExtended(_unlockTime);
    }

    /// @dev Exits the lock and keeps MTA in contract
    /// @return mtaBalance Balance of MTA in this contract
    function exitLock() external override returns (uint256 mtaBalance) {
        _onlyGovernors();

        votingLockup.exit();

        emit LockExited();
    }

    /// @dev Changes the address of the VotingLockup
    /// WARNING - this approves mta on the new contract, so should be taken with care
    /// @param _newLock Address of the new VotingLockup
    function changeLockAddress(address _newLock) external override {
        _onlyGovernance();

        require(votingLockup.balanceOf(address(this)) == 0, "Active lockup");

        votingLockup = IMStableVotingLockup(_newLock);

        IERC20Upgradeable(mta).safeApprove(_newLock, type(uint256).max);

        emit LockChanged(_newLock);
    }

    /// @dev Changes the percentage of MTA earned via staking that gets redistributed to strategies
    /// @param _newRate Scaled pct of earnings to redistribute to strategies, where 100% = 10000
    function changeRedistributionRate(uint256 _newRate) external override {
        _onlyGovernors();

        require(_newRate < MAX_RATE, "Invalid rate");

        redistributionRate = _newRate;

        emit RedistributionRateChanged(_newRate);
    }

    /***************************************
                        LOANS
    ****************************************/

    /// @dev Loans the voter proxy a given amt by transferring and logging
    /// @param _amt Amt to send to the proxy!
    function loan(uint256 _amt) external override {
        require(loans[msg.sender] == 0, "Existing loan");

        mta.safeTransferFrom(msg.sender, address(this), _amt);
        loans[msg.sender] = _amt;

        emit Loaned(msg.sender, _amt);
    }

    /// @dev Repays the initially loaned MTA amount to a creditor
    /// @param _creditor Address of the initial creditor
    function repayLoan(address _creditor) external override {
        _onlyGovernors();

        uint256 loanAmt = loans[_creditor];
        require(loanAmt != 0, "Non-existing loan");

        loans[_creditor] = 0;
        mta.safeTransfer(_creditor, loanAmt);

        emit LoanRepaid(_creditor, loanAmt);
    }

    /***************************************
                    STRATEGIES
    ****************************************/

    /// @dev Adds a new supported strategy, looking up want and approving to vault
    /// @param _strategy Address of the BadgerStrategy
    /// @param _vault Address of the mStable vault
    function supportStrategy(address _strategy, address _vault) external override {
        _onlyGovernance();

        require(address(strategyToVault[_strategy]) == address(0), "Strategy already supported");

        uint256 len = strategies.length;
        for (uint256 i = 0; i < len; i++) {
            address vaulti = address(strategyToVault[strategies[i]]);
            require(vaulti != _vault, "Vault already supported");
        }

        // Lookup want in strategy
        address want = IStrategy(_strategy).want();
        // Approve spending to vault
        IERC20Upgradeable(want).safeApprove(_vault, type(uint256).max);
        // Whitelist strategy
        strategyToVault[_strategy] = IMStableBoostedVault(_vault);
        strategies.push(_strategy);

        emit StrategyAdded(_strategy, _vault);
    }

    /***************************************
                    POOL
    ****************************************/

    /// @dev Simply stakes in pool
    /// NOTE - Assumes that the want has already been transferred here
    /// @param _amt Amt of want that should be staked in the vault
    function deposit(uint256 _amt) external override {
        IMStableBoostedVault vault = _onlyActiveStrategy();

        vault.stake(_amt);
    }

    /// @dev Withdraws balance from vault, returning to strategy
    /// Passes _want to avoid having to read _want again via ext call
    /// @param _want Address of the LP token to return back to sender
    function withdrawAll(address _want) external override {
        IMStableBoostedVault vault = _onlyActiveStrategy();

        uint256 rawBal = vault.rawBalanceOf(address(this));
        vault.withdraw(rawBal);
        IERC20Upgradeable(_want).safeTransfer(msg.sender, rawBal);
    }

    /// @dev Withdraws _amt from vault, returning to strategy
    /// Passes _want to avoid having to read _want again via ext call
    /// @param _want Address of the LP token to return back to sender
    /// @param _amt Amount of want to withdraw and return
    function withdrawSome(address _want, uint256 _amt) external override {
        IMStableBoostedVault vault = _onlyActiveStrategy();

        vault.withdraw(_amt);
        IERC20Upgradeable(_want).safeTransfer(msg.sender, _amt);
    }

    /// @dev Claims rewards from the matching vault, and returns them to sender.
    /// @return immediateUnlock Amount of tokens that were earned without need for vesting
    /// @return vested Amount of tokens that were earned post-vesting
    function claim() external override returns (uint256 immediateUnlock, uint256 vested) {
        IMStableBoostedVault vault = _onlyActiveStrategy();

        // Get balance of MTA before (there could be residual MTA here waiting to be reinvested in vMTA)
        uint256 balBefore = mta.balanceOf(address(this));
        // Get MTA ready for immediate unlock (this is a view fn)
        immediateUnlock = vault.earned(address(this));
        // Actually claim rewards - both immediately unlocked as well as post-vesting rewards
        vault.claimRewards();
        // Calc the total amount claimed based on changing bal
        uint256 balAfter = mta.balanceOf(address(this));
        uint256 totalClaimed = balAfter.sub(balBefore);
        // Amount of the claim that was subject to vesting
        vested = totalClaimed.sub(immediateUnlock);

        mta.safeTransfer(msg.sender, totalClaimed);
    }
}
