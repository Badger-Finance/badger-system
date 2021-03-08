// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

/*
    All Sett contracts inherit from this.

    Changelog:
    
    V1.1
    * Strategist no longer has special function calling permissions
    * Version function added to contract
    * All write functions, with the exception of transfer, are pausable
    * Keeper or governance can pause
    * Only governance can unpause
    
    V1.2
    * Transfer functions are now pausable along with all other non-permissioned write functions
    * All permissioned write functions, with the exception of pause() & unpause(), are pausable as well

    V1.3
    * Add global defender w/ pause/freeze capabilities.
*/
contract SettVersion {
    function version() public view returns (string memory) {
        return "1.3";
    }
}
