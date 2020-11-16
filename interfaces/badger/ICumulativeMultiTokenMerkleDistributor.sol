// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.5.0;

/*
    Cumulative Merkle distributor
*/
interface ICumulativeMultiTokenMerkleDistributor {

    /// @notice Emit when insufficient funds to handle incoming root totals
    event InsufficientFundsForRoot(bytes32 indexed root);
    event RootUpdated(uint256 indexed cycle, bytes32 indexed root, bytes32 indexed contentHash, uint256 timestamp);
    event Claimed(address indexed user, address indexed token, uint256 amount, uint256 indexed cycle, uint256 timestamp);

    /// @notice Claim accumulated rewards for a set of tokens at a given cycle number
    // function claim(address[] tokens, uint256 cycle, bytes[] memory proof) external;
}