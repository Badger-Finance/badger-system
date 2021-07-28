// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "interfaces/badger/ISett.sol";
import "interfaces/badger/IStrategy.sol";

contract KeeperAccessControl is AccessControlUpgradeable {
    // Keeper Roles
    bytes32 public constant HARVESTER_ROLE = keccak256("HARVESTER_ROLE");
    bytes32 public constant TENDER_ROLE = keccak256("TENDER_ROLE");
    bytes32 public constant EARNER_ROLE = keccak256("EARNER_ROLE");

    function initialize(address initialAdmin_) external initializer {
        __AccessControl_init();
        _setupRole(DEFAULT_ADMIN_ROLE, initialAdmin_);
    }

    // ===== Permissioned Functions: Earner (Move money into strategy positions) =====
    function deposit(address strategy) external {
        require(hasRole(EARNER_ROLE, msg.sender), "EARNER_ROLE");
        IStrategy(strategy).deposit();
    }

    function earn(address sett) external {
        require(hasRole(EARNER_ROLE, msg.sender), "EARNER_ROLE");
        ISett(sett).earn();
    }

    // ===== Permissioned Functions: Tender =====
    function tend(address strategy) external {
        require(hasRole(TENDER_ROLE, msg.sender), "TENDER_ROLE");
        IStrategy(strategy).tend();
    }

    // ===== Permissioned Functions: Harvester =====
    function harvest(address strategy) external {
        require(hasRole(HARVESTER_ROLE, msg.sender), "HARVESTER_ROLE");
        IStrategy(strategy).harvest();
    }
}
