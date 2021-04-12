// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

interface IMStableVoterProxy {
    // VOTING LOCKUP

    // Init lock in VotingLock
    function createLock() external;

    // Claims MTA rewards from Staking and reinvests
    function reinvestMta() external;

    // Exits the lock and keeps MTA in contract
    function exitLock() external returns (uint256 mtaBalance);

    // Upgrades the lock address
    function changeLockAddress(address _newLock, uint256 _endTime) external;

    // Repays the initially loaned MTA amount
    function repayLoan() external;

    // STRATEGIES

    // Adds a new supported strategy, looking up want and approving to vault
    function supportStrategy(address _strategy, address _vault) external;

    // POOL

    // Transfers _amt from sender and deposits to pool
    function deposit(address _token, uint256 _amt) external;

    // Withdraws balance from vault, returning to strategy
    function withdrawAll() external;

    // Withdraws _amt from vault, returning to strategy
    function withdrawSome(uint256 _amt) external;

    // fetch immediate unlock and then claim all & xfer
    // return subtracted amt
    function claim() external returns (uint256 vestedMta);
}
