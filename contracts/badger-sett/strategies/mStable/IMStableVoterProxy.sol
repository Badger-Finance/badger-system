// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

interface IMStableVoterProxy {
    // VOTING LOCKUP

    // Init lock in VotingLock
    function createLock(uint256 _endTime) external;

    // Claims MTA rewards from Staking and reinvests
    function reinvestMta() external;

    // Extends lockup period
    function extendLock() external;

    // Exits the lock and keeps MTA in contract
    function exitLock() external returns (uint256 mtaBalance);

    // Upgrades the lock address
    function changeLockAddress(address _newLock) external;

    // LOANS

    function loan(uint256 _amt) external;

    // Repays the initially loaned MTA amount
    function repayLoan(address _creditor) external;

    // STRATEGIES

    // Adds a new supported strategy, looking up want and approving to vault
    function supportStrategy(address _strategy, address _vault) external;

    // POOL

    // Simply stakes in pool
    function deposit(uint256 _amt) external;

    // Withdraws balance from vault, returning to strategy
    function withdrawAll(address _want) external;

    // Withdraws _amt from vault, returning to strategy
    function withdrawSome(address _want, uint256 _amt) external;

    // fetch immediate unlock and then claim all & xfer
    // return subtracted amt
    function claim() external returns (uint256 vestedMta);
}
