// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "interfaces/remote/IPauser.sol";

/*
    RemotePauserUpgradeable only handles paused state for msg.sender (only msg.sender can modifies his own state)
    and takes care of state storage away from the originating contract.
 */
contract RemotePauserUpgradeable {
    mapping(address => bool) private _paused;

    function paused() external view returns (bool) {
        return _paused[msg.sender];
    }

    function pause() external {
        _paused[msg.sender] = true;
    }

    function unpause() external {
        _paused[msg.sender] = false;
    }

    // Reserve storage space for upgrades.
    uint256[49] private __gap;
}
