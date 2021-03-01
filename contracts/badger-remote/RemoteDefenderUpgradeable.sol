// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

import "./RemotePauserUpgradeable.sol";
import "./RemoteFreezerUpgradeable.sol";

/*
    RemoteDefenderUpgradeable defends against unapproved address access.
    It also handles freezing/pausing of contract addresses and EOAs.
 */
contract RemoteDefenderUpgradeable is OwnableUpgradeable, RemoteFreezerUpgradeable, RemotePauserUpgradeable {
    mapping(address => bool) private _approved;

    function initialize() public initializer {
        __Ownable_init();
    }

    function approved(address account) external view returns (bool) {
        return _approved[account];
    }

    function approve(address account) external onlyOwner {
        _approved[account] = true;
    }

    function revoke(address account) external onlyOwner {
        _approved[account] = false;
    }

    // Reserve storage space for upgrades.
    uint256[49] private __gap;
}
