// SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "interfaces/badger/IAddressWhitelist.sol";

contract AddressWhitelist is OwnableUpgradeable, IAddressWhitelist {
    mapping(address => bool) public whitelist;

    function initialize() public initializer {
        __Ownable_init();
    }

    function exists(address _addr) external override returns (bool) {
        return whitelist[_addr];
    }

    // ==== ADMIN FUNCTIONS ====

    function add(address _addr) external onlyOwner {
        whitelist[_addr] = true;
    }

    function remove(address _addr) external onlyOwner {
        if (whitelist[_addr]) {
            delete whitelist[_addr];
        }
    }
}
