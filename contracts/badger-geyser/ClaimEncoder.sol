// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

contract ClaimEncoder {
    function encodeClaim(
        address[] calldata tokens,
        uint256[] calldata cumulativeAmounts,
        uint256 index,
        uint256 cycle,
        address account
    ) public view returns (bytes memory encoded, bytes32 hash) {
        encoded = abi.encodePacked(index, account, cycle, tokens, cumulativeAmounts);
        hash = keccak256(encoded);
    }
}
