// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "interfaces/remote/IRemotePauser.sol";

/*
    PauseableStorageless is a no-storage required inheritable version of OZ's Pauseable contract. 
    Contracts may safely inherit this w/o messing up their internal storage layout.
 */
contract PauseableStorageless {
    /**
     * @dev Emitted when the pause is triggered by `account`.
     */
    event Paused(address account);

    /**
     * @dev Emitted when the pause is lifted by `account`.
     */
    event Unpaused(address account);

    /**
     * @dev Modifier to make a function callable only when the contract is not paused.
     *
     * Requirements:
     *
     * - The contract must not be paused.
     */
    modifier whenNotPaused(address pauser) {
        require(!IRemotePauser(pauser).paused(), "Pausable: paused");
        _;
    }

    /**
     * @dev Modifier to make a function callable only when the contract is paused.
     *
     * Requirements:
     *
     * - The contract must be paused.
     */
    modifier whenPaused(address pauser) {
        require(IRemotePauser(pauser).paused(), "Pausable: not paused");
        _;
    }

    /**
     * @dev Triggers stopped state.
     *
     * Requirements:
     *
     * - The contract must not be paused.
     */
    function _pause(address pauser) internal virtual whenNotPaused {
        IRemotePauser(pauser).pause();  
        emit Paused(msg.sender);
    }

    /**
     * @dev Returns to normal state.
     *
     * Requirements:
     *
     * - The contract must be paused.
     */
    function _unpause() internal virtual whenPaused {
        IRemotePauser(pauser).unpause();  
        emit Unpaused(msg.sender);
    }
}
