// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

/// @title  IMStableVoterProxy
/// @author mStable
/// @notice VoterProxy that deposits into mStable vaults and uses MTA stake to boosts rewards.
/// @dev    Receives MTA from Strategies and Loans in order to bolster Stake. Any MTA held here is
///         assumed to be invested to staking.
interface IMStableVoterProxy {
    /***************************************
                    VOTINGLOCK
    ****************************************/

    function createLock(uint256 _endTime) external;

    function harvestMta() external;

    function extendLock(uint256 _unlockTime) external;

    function exitLock() external returns (uint256 mtaBalance);

    function changeLockAddress(address _newLock) external;

    function changeRedistributionRate(uint256 _newRate) external;

    /***************************************
                        LOANS
    ****************************************/

    function loan(uint256 _amt) external;

    function repayLoan(address _creditor) external;

    /***************************************
                    STRATEGIES
    ****************************************/

    function supportStrategy(address _strategy, address _vault) external;

    /***************************************
                    POOL
    ****************************************/

    function deposit(uint256 _amt) external;

    function withdrawAll(address _want) external;

    function withdrawSome(address _want, uint256 _amt) external;

    function claim() external returns (uint256 immediateUnlock, uint256 vested);
}
