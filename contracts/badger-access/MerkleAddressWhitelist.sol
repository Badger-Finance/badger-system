// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import "interfaces/badger/IMerkleAddressWhitelist.sol";

contract MerkleAddressWhitelist is OwnableUpgradeable, IMerkleAddressWhitelist {
    bytes32 public merkleRoot;

    function initialize(bytes32 _merkleRoot) public initializer {
        __Ownable_init();
        merkleRoot = _merkleRoot;
    }

    function exists(address addr, bytes32[] calldata merkleProof) external override returns (bool) {
        // Verify the merkle proof and existence of token in whitelist.
        bytes32 node = keccak256(abi.encodePacked(addr));
        return MerkleProofUpgradeable.verify(merkleProof, merkleRoot, node);
    }

    // ==== ADMIN FUNCTIONS ====

    // Update whitelist merkle root.
    function update(bytes32 _merkleRoot) external onlyOwner {
        merkleRoot = _merkleRoot;
    }
}
