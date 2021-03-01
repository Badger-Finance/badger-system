// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "interfaces/remote/IRemoteDefender.sol";

import "./PauseableStorageless.sol";

/*
    DefenderStorageless is a no-storage required inheritable defender of unapproved contract access.
    Contracts may safely inherit this w/o messing up their internal storage layout.
 */
contract DefenderStorageless is PauseableStorageless {
    // Defend against access by unapproved contracts (EOAs are allowed access).
    modifier defend(address defender) {
        require(IRemoteDefender(defender).approved(msg.sender) || msg.sender == tx.origin, "Access denied for caller");
        _;
    }
}
