// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "interfaces/badger/ISett.sol";
import "interfaces/badger/IStrategy.sol";
import "interfaces/badger/IStabilizerStrategy.sol";
import "interfaces/mStable/IMStableVoterProxy.sol";

contract KeeperAccessControl is AccessControlUpgradeable {
    // Keeper Roles
    bytes32 public constant HARVESTER_ROLE = keccak256("HARVESTER_ROLE");
    bytes32 public constant TENDER_ROLE = keccak256("TENDER_ROLE");
    bytes32 public constant EARNER_ROLE = keccak256("EARNER_ROLE");

    function initialize(address initialAdmin_) external initializer {
        __AccessControl_init();
        _setupRole(DEFAULT_ADMIN_ROLE, initialAdmin_);
    }

    modifier settBalanceCheck(address sett) {
        uint256 balanceOfBefore = ISett(sett).balance();
        _;
        uint256 balanceOfAfter = ISett(sett).balance();
        require(balanceOfAfter >= balanceOfBefore, "Sett balance must not decrease");
    }

    modifier strategyBalanceCheck(address strategy) {
        uint256 balanceOfBefore = IStrategy(strategy).balanceOf();
        _;
        uint256 balanceOfAfter = IStrategy(strategy).balanceOf();
        require(balanceOfAfter >= balanceOfBefore, "Strategy balance must not decrease");
    }

    // ===== Permissioned Functions: Earner (Move money into strategy positions) =====
    function deposit(address strategy) external strategyBalanceCheck(strategy) {
        require(hasRole(EARNER_ROLE, msg.sender), "EARNER_ROLE");
        IStrategy(strategy).deposit();
    }

    function earn(address sett) external settBalanceCheck(sett) {
        require(hasRole(EARNER_ROLE, msg.sender), "EARNER_ROLE");
        ISett(sett).earn();
    }

    // ===== Permissioned Functions: Tender =====
    function tend(address strategy) external strategyBalanceCheck(strategy) {
        require(hasRole(TENDER_ROLE, msg.sender), "TENDER_ROLE");
        IStrategy(strategy).tend();
    }

    // ===== Permissioned Functions: Harvester =====
    function harvest(address strategy) external strategyBalanceCheck(strategy) returns (uint256) {
        require(hasRole(HARVESTER_ROLE, msg.sender), "HARVESTER_ROLE");
        return IStrategy(strategy).harvest();
    }

    function harvestNoReturn(address strategy) external strategyBalanceCheck(strategy) {
        require(hasRole(HARVESTER_ROLE, msg.sender), "HARVESTER_ROLE");
        IStrategy(strategy).harvest();
    }

    function harvestMta(address voterProxy) external {
        require(hasRole(HARVESTER_ROLE, msg.sender), "HARVESTER_ROLE");
        IMStableVoterProxy(voterProxy).harvestMta();
    }

    function rebalance(address strategy) external {
        require(hasRole(HARVESTER_ROLE, msg.sender), "HARVESTER_ROLE");
        IStabilizerStrategy(strategy).rebalance();
    }
}
