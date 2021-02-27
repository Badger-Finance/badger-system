// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

// Track underlying version of all Sett forks in one place.
contract SettVersion {
    function version() public view returns (string memory) {
        return "1.3";
    }
}
