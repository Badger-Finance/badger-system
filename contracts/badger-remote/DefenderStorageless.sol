// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "interfaces/remote/IRemoteDefender.sol";

/*
    DefenderStorageless is a no-storage required inheritable defender of unapproved contract access.
    Contracts may safely inherit this w/o messing up their internal storage layout.
 */
contract DefenderStorageless {
    // Defend against access by unapproved contracts (EOAs are allowed access).
    modifier defend(address defender) {
        require(IRemoteDefender(defender).approved(msg.sender) || msg.sender == tx.origin, "Access denied for caller");
        require(!IRemoteDefender(defender).frozen(msg.sender), "Caller frozen");
        _;
    }
}
