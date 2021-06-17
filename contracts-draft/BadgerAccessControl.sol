// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";

contract BadgerAccessControl is AccessControlUpgradeable, PausableUpgradeable {
    function initialize(address _admin) external initializer {
        __AccessControl_init_unchained();
        __Pausable_init_unchained();
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
    }
    // Markets
    bytes32 public constant UNI_V2_LIKE_ROUTER_ROLE = keccak256("UNI_V2_LIKE_ROUTER_ROLE");
    bytes32 public constant CRV_LIKE_ROUTER_ROLE = keccak256("CRV_LIKE_ROUTER_ROLE");
}
