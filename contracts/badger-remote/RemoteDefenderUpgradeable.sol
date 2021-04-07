// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

/*
    RemoteDefenderUpgradeable defends against unapproved address access.
    It handles the following protective functionality (of contract addresses and EOAs):
        - approved for contract specific or global access
        - frozen from global access
        - paused specific contract or globally
 */
contract RemoteDefenderUpgradeable is OwnableUpgradeable {
    // Is contract address approved for global access?
    mapping(address => bool) private _approvedGlobal;
    // Is contract address approved for targeted access to msg.sender?
    mapping(address => mapping(address => bool)) private _approvedTargeted;

    // Is account address frozen?
    mapping(address => bool) private _frozen;

    // Is contract address paused?
    mapping(address => bool) private _paused;
    // Is everything paused globally?
    bool private _pausedGlobal;

    function initialize() public initializer {
        __Ownable_init();
    }

    // Access control functions.
    function approved(address account) external view returns (bool) {
        if (_approvedTargeted[account][msg.sender]) {
            return true;
        }
        return _approvedGlobal[account];
    }

    function approve(address account) external onlyOwner {
        _approvedGlobal[account] = true;
    }

    function revoke(address account) external onlyOwner {
        _approvedGlobal[account] = false;
    }

    function approveFor(address account, address target) external onlyOwner {
        _approvedTargeted[account][target] = true;
    }

    function revokeFor(address account, address target) external onlyOwner {
        _approvedTargeted[account][target] = false;
    }

    // Freezer functions.
    function frozen(address account) external view returns (bool) {
        return _frozen[account];
    }

    function freeze(address account) external onlyOwner {
        _frozen[account] = true;
    }

    function unfreeze(address account) external onlyOwner {
        _frozen[account] = false;
    }

    // Pauser functions.
    function paused() external view returns (bool) {
        return _pausedGlobal || _paused[msg.sender];
    }

    function pauseGlobal() external onlyOwner {
        _pausedGlobal = true;
    }

    function unpauseGlobal() external onlyOwner {
        _pausedGlobal = false;
    }

    function pause() external {
        _paused[msg.sender] = true;
    }

    function unpause() external {
        _paused[msg.sender] = false;
    }

    // Reserve storage space for upgrades.
    uint256[50] private __gap;
}
