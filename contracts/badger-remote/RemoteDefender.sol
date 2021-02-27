// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

/*
    RemoteDefender defends against unapproved address access.
 */
contract RemoteDefender is OwnableUpgradeable {
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
}
