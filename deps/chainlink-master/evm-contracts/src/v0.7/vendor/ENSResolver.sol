// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

abstract contract ENSResolver {
    function addr(bytes32 node) public virtual view returns (address);
}
