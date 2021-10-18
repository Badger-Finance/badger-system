// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "interfaces/badger/IKeeperAccessControl.sol";

contract FlashbotsHarvester is AccessControlUpgradeable, ReentrancyGuardUpgradeable {
    address public keeperAcl;
    bytes32 public constant HARVESTER_ROLE = keccak256("HARVESTER_ROLE");

    function initialize(
        address admin,
        address initialHarvester,
        address _keeperAcl
    ) public initializer {
        __AccessControl_init();

        _setupRole(DEFAULT_ADMIN_ROLE, admin);
        _setupRole(HARVESTER_ROLE, initialHarvester);
        keeperAcl = _keeperAcl;
    }

    /// ===== Modifiers =====

    // * @param _keeperAcl Address of KeeperAccessControl contract
    function setKeeperAcl(address _keeperAcl) external {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "DEFAULT_ADMIN_ROLE");
        keeperAcl = _keeperAcl;
    }

    // * @param strategy Address of strategy to harvest
    // * @param minHarvestedExpected Min amount of want expected to be harvested
    function harvest(address strategy, uint256 minHarvestExpected) external payable nonReentrant {
        require(hasRole(HARVESTER_ROLE, msg.sender), "HARVESTER_ROLE");

        uint256 harvested = IKeeperAccessControl(keeperAcl).harvest(strategy);
        require(harvested >= minHarvestExpected, "Harvest is too low");

        block.coinbase.call{value: msg.value}(new bytes(0));
    }
}
