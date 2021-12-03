// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/EnumerableSetUpgradeable.sol";

/**
 * @title Badger Geyser
 @dev Tracks stakes and pledged tokens to be distributed, for use with 
 @dev BadgerTree merkle distribution system. An arbitrary number of tokens to 
 distribute can be specified.
 */

contract GlobalAccessControl is Initializable, AccessControlUpgradeable, PausableUpgradeable {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using SafeMathUpgradeable for uint256;
    using EnumerableSetUpgradeable for EnumerableSetUpgradeable.AddressSet;

    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant UNPAUSER_ROLE = keccak256("UNPAUSER_ROLE");

    bytes32 public constant BLACKLIST_MANAGER_ROLE = keccak256("BLACKLIST_MANAGER_ROLE");
    bytes32 public constant BLACKLISTED_ROLE = keccak256("BLACKLISTED_ROLE");

    function initialize() external initializer {
        bool public transfersEnabled;
        bool public depositsEnabled;
        bool public withdrawalsEnabled;
        /**
            Admin manages roles for pausers, unpausers, and blacklist managers
            Blacklist Manager manages blacklist

        */

        // _setRoleAdmin(PAUSER_ROLE, DEFAULT_ADMIN_ROLE);
        // _setRoleAdmin(UNPAUSER_ROLE, DEFAULT_ADMIN_ROLE);
        // _setRoleAdmin(BLACKLIST_MANAGER_ROLE, DEFAULT_ADMIN_ROLE);

        _setRoleAdmin(BLACKLISTED_ROLE, BLACKLIST_MANAGER_ROLE);
        _setupRole(DEFAULT_ADMIN_ROLE, 0xB65cef03b9B89f99517643226d76e286ee999e77);
        _setupRole(BLACKLIST_MANAGER_ROLE, 0x86cbD0ce0c087b482782c181dA8d191De18C8275);

        _setupRole(PAUSER_ROLE, 0xB65cef03b9B89f99517643226d76e286ee999e77);
        _setupRole(UNPAUSER_ROLE, 0xB65cef03b9B89f99517643226d76e286ee999e77);
    }

    function pause() external {
        require(hasRole(PAUSER_ROLE, msg.sender), "PAUSER_ROLE");
        _pause();
    }

    function unpause() external {
        require(hasRole(UNPAUSER_ROLE, msg.sender), "UNPAUSER_ROLE");
        _unpause();
    }

    function isBlacklisted(address account) external returns (bool) {
        return hasRole(BLACKLISTED_ROLE, account);
    }
}
