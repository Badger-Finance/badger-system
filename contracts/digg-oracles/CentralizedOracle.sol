// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";

import "interfaces/digg/IMedianOracle.sol";

contract CentralizedOracle is AccessControlUpgradeable, PausableUpgradeable {
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");

    address public medianOracle;

    uint256 public proposedPayload;
    address public lastProposer;

    event PushReport(uint256 payload);

    function initialize(
        address medianOracle_,
        address initialAdmin_,
        address initialGuardian_,
        address[] memory initialOracles_
    ) external initializer {
        __AccessControl_init();
        __Pausable_init_unchained();

        medianOracle = medianOracle_;

        _setupRole(DEFAULT_ADMIN_ROLE, initialAdmin_);
        _setupRole(GUARDIAN_ROLE, initialGuardian_);

        for (uint256 i = 0; i < initialOracles_.length; i++) {
            _setupRole(ORACLE_ROLE, initialOracles_[i]);
        }
    }

    // ===== Access Control Modifiers =====
    modifier onlyOracle() {
        require(hasRole(ORACLE_ROLE, msg.sender), "ORACLE_ROLE");
        _;
    }

    modifier onlyGuardian() {
        require(hasRole(GUARDIAN_ROLE, msg.sender), "GUARDIAN_ROLE");
        _;
    }

    // ===== Permissioned Actions: Oracle =====
    function proposeReport(uint256 payload) public onlyOracle {
        lastProposer = msg.sender;
        proposedPayload = payload;
    }

    // Any oracle account other than the proposer can approve a proposed update
    function approveReport(uint256 payload) public onlyOracle {
        require(msg.sender != lastProposer, "Report proposer cannot approve own report");
        require(payload == proposedPayload, "Proposed payload must match");
        IMedianOracle(medianOracle).pushReport(proposedPayload);
    }

    // ===== Permissioned Actions: Guardian =====
    function pause() public onlyGuardian {
        pause();
    }

    function unpause() public onlyGuardian {
        unpause();
    }
}
