// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/MathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";

import "interfaces/mStable/IMStableAsset.sol";
import "interfaces/mStable/IMStableNexus.sol";
import "interfaces/mStable/IMStableBoostedVault.sol";
import "interfaces/mStable/IMStableVotingLockup.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IStrategy.sol";

import "../../SettAccessControl.sol";

import "./IMStableVoterProxy.sol";

// Dumb contract that:
//  - manages stake in mStable staking https://governance.mstable.org/#/stake
//  - deposits & withdraws from mStable vaults
//  - claims rewards from mStable vaults and returns to sender
//  - returns balance of caller in vault
// Extra:
//  - migrate from staking v1 to v2
//  - pay back loan if any
//  - direct boost if required
contract MStableVoterProxy is IMStableVoterProxy, PausableUpgradeable, SettAccessControl {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    mapping(address => IMStableBoostedVault) public strategyToVault; // strategy => vault
    mapping(address => address) public vaultToStrategy; // used to ensure vault is singleton

    IMStableNexus public nexus;
    IMStableVotingLockup public votingLockup;

    mapping(address => uint256) public loans;
    IERC20Upgradeable public constant mta = IERC20Upgradeable(0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2);

    function initialize(
        address _governance,
        address _strategist,
        address _keeper,
        address[2] memory _config
    ) public initializer {
        __Pausable_init();
        governance = _governance;
        strategist = _strategist;
        keeper = _keeper;

        votingLockup = IMStableVotingLockup(_config[0]);
        nexus = IMStableNexus(_config[1]);

        IERC20Upgradeable(mta).safeApprove(votingLockup, type(uint256).max);
    }

    function _onlyActiveStrategy() internal view returns (IMStableBoostedVault vault) {
        vault = strategyToVault[msg.sender];
        require(address(vault) != address(0), "onlyStrategy");
    }

    // both badgerDAO multisig and mStableDAO multisig
    function _onlyGovernors() internal view {
        require(msg.sender == governance || msg.sender == nexus.governor(), "onlyGovernors");
    }

    // VOTING LOCKUP

    // Init lock in VotingLock
    function createLock(uint256 _unlockTime) external override {
        _onlyGovernors();

        uint256 bal = mta.balanceOf(address(this));
        votingLockup.createLock(bal, _unlockTime);
    }

    // Claims MTA rewards from Staking and reinvests
    function reinvestMta() external override {
        _onlyGovernors();

        votingLockup.claimReward();
        uint256 bal = mta.balanceOf(address(this));
        votingLockup.increaseLockAmount(bal);
    }

    function extendLock(uint256 _unlockTime) external override {
        _onlyGovernors();

        votingLockup.increaseLockLength(_unlockTime);
    }

    // Exits the lock and keeps MTA in contract
    function exitLock() external override returns (uint256 mtaBalance) {
        _onlyGovernors();

        votingLockup.exit();
    }

    // Upgrades the lock address
    // IMPORTANT - approves _newLock to spend MTA. This could be dangerous
    function changeLockAddress(address _newLock) external override {
        _onlyGovernors();

        require(votingLockup.balanceOf(address(this)) == 0, "Active lockup");

        votingLockup = IMStableVotingLockup(_newLock);

        IERC20Upgradeable(mta).safeApprove(_newLock, type(uint256).max);
    }

    // LOANS

    // Loans the voter proxy a given amt
    function loan(uint256 _amt) external override {
        require(loans[msg.sender] == 0, "Existing loan");

        mta.safeTransferFrom(msg.sender, address(this), value);
        loans[msg.sender] = _amt;
    }

    // Repays the initially loaned MTA amount
    function repayLoan(address _creditor) external override {
        _onlyGovernors();

        uint256 loanAmt = loans[_creditor];
        require(loanAmt != 0, "Non-existing loan");

        loans[_creditor] = 0;
        mta.safeTransfer(_creditor, loanAmt);
    }

    // STRATEGIES

    // Adds a new supported strategy, looking up want and approving to vault
    function supportStrategy(address _strategy, address _vault) external override {
        _onlyGovernors();

        require(vaultToStrategy[_vault] == address(0), "Vault already supported");

        // Lookup want in strategy
        address want = IStrategy(_strategy).want();
        // Approve spending to vault
        IERC20Upgradeable(want).safeApprove(_vault, type(uint256).max);
        // Whitelist strategy
        strategyToVault[_strategy] = IMStableBoostedVault(_vault);
        vaultToStrategy[_vault] = _strategy;
    }

    // POOL

    // Simply stakes in pool
    function deposit(uint256 _amt) external override {
        address vault = _onlyActiveStrategy();

        vault.stake(_amt);
    }

    // Withdraws balance from vault, returning to strategy
    // Passes _want to avoid having to read _want again via ext call
    function withdrawAll(address _want) external override {
        address vault = _onlyActiveStrategy();

        uint256 rawBal = vault.rawBalanceOf(address(this));
        vault.withdraw(rawBal);
        IMStableAsset(_want).safeTransfer(msg.sender, rawBal);
    }

    // Withdraws _amt from vault, returning to strategy
    // Passes _want to avoid having to read _want again via ext call
    function withdrawSome(address _want, uint256 _amt) external override {
        address vault = _onlyActiveStrategy();

        vault.withdraw(_amt);
        IMStableAsset(_want).safeTransfer(msg.sender, _amt);
    }

    // fetch immediate unlock and then claim all & xfer
    function claim() external override returns (uint256 immediateUnlock, uint256 vested) {
        address vault = _onlyActiveStrategy();

        // Get balance of MTA before (there could be residual MTA here waiting to be reinvested in vMTA)
        uint256 balBefore = mta.balanceOf(address(this));
        // Get MTA ready for immediate unlock, this is a view fn
        immediateUnlock = vault.earned(address(this));
        vault.claimRewards();
        // Calc the total amount claimed based on changing bal
        uint256 balAfter = mta.balanceOf(address(this));
        uint256 totalClaimed = balAfter.sub(balBefore);
        // Amount of the claim that was subject to vesting
        vested = totalClaimed.sub(immediateUnlock);

        mta.safeTransfer(msg.sender, totalClaimed);
    }
}
