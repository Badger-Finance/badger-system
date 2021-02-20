// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

contract ClaimEncoder {
    function encodeClaim(
        address[] calldata tokens,
        uint256[] calldata cumulativeAmounts,
        address account,
        uint256 index,
        uint256 cycle
    ) public view returns (bytes memory encoded, bytes32 hash) {
        encoded = abi.encode(index, account, cycle, tokens, cumulativeAmounts);
        hash = keccak256(encoded);
    }
}
