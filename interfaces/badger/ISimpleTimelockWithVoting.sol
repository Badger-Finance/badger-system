//SPDX-License-Identifier: Unlicense
pragma solidity >=0.5.0 <0.8.0;
interface ISimpleTimelockWithVoting {
    function release() external;

    /**
     * @notice Allows the timelock to call arbitrary contracts, as long as it does not reduce it's locked token balance
     * @dev Initialization check is implicitly provided by `voteExists()` as new votes can only be
     *      created via `newVote(),` which requires initialization
     * @param to Contract address to call
     * @param value ETH value to send, if any
     * @param data Encoded data to send
     */
    function call(
        address to,
        uint256 value,
        bytes calldata data
    ) external payable returns (bool success);
}
