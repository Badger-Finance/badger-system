// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";

contract ContributorLogger is AccessControlUpgradeable {
    using SafeMathUpgradeable for uint256;
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");

    uint256 public nextId;

    struct Entry {
        address recipient;
        address token;
        uint128 amount;
        uint32 amountDuration;
        uint40 startTime;
        uint40 endTime;
    }

    mapping(uint256 => Entry) public paymentEntries;

    // ===== Events =====
    event CreateEntry(
        uint256 indexed id,
        address indexed recipient,
        address token,
        uint128 amount,
        uint32 amountDuration,
        uint40 startTime,
        uint40 endTime,
        uint256 indexed timestamp,
        uint256 blockNumber
    );

    event UpdateEntry(
        uint256 indexed id,
        uint256 indexed updatedId,
        uint128 amount,
        uint32 amountDuration,
        uint40 startTime,
        uint40 endTime,
        uint256 indexed timestamp,
        uint256 blockNumber
    );

    event DeleteEntry(uint256 indexed id, uint256 indexed timestamp, uint256 blockNumber);

    function initialize(
        address multisendLib_,
        address initialAdmin_,
        address initialManager_
    ) external initializer {
        __AccessControl_init();

        _setupRole(DEFAULT_ADMIN_ROLE, initialAdmin_);
        _setupRole(MANAGER_ROLE, initialManager_);
    }

    modifier onlyManager() {
        require(hasRole(MANAGER_ROLE, msg.sender), "onlyManager");
        _;
    }

    // ===== View Functions =====
    function getEntry(uint256 id)
        public
        view
        returns (
            address,
            address,
            uint128,
            uint32,
            uint40,
            uint40
        )
    {
        Entry storage entry = paymentEntries[id];
        return (entry.recipient, entry.token, entry.amount, entry.amountDuration, entry.startTime, entry.endTime);
    }

    // ===== Permissioned Functions: Manager =====

    /// @dev Stream a token to a recipient over time.
    /// @dev Amount / amountDuration defines the rate per second.
    /// @dev This rate will persist from the start time until the end time.
    /// @dev The start time should not be in the past.
    /// @dev To create an eternal entry, use maxuint256 as end time. The stream will then persist until deleted or updated.
    function createEntry(
        address recipient,
        address token,
        uint128 amount,
        uint32 amountDuration,
        uint40 startTime,
        uint40 endTime
    ) external onlyManager {
        require(startTime >= block.timestamp, "start time cannot be in past");
        uint256 newId = _createEntry(recipient, token, amount, amountDuration, startTime, endTime);
        emit CreateEntry(newId, recipient, token, amount, amountDuration, startTime, endTime, block.timestamp, block.number);
    }

    /// @dev Update a stream by changing the rate or time parameters.
    /// @dev The recipient and amount cannot be updated on an entry.
    function updateEntry(
        uint256 id,
        uint128 amount,
        uint32 amountDuration,
        uint40 startTime,
        uint40 endTime
    ) external onlyManager {
        require(id < nextId, "ID does not exist");
        require(startTime >= block.timestamp, "start time cannot be in past");
        Entry memory entry = paymentEntries[id];
        uint256 newId = _createEntry(entry.recipient, entry.token, amount, amountDuration, startTime, endTime);
        emit UpdateEntry(newId, id, amount, amountDuration, startTime, endTime, block.timestamp, block.number);
    }

    /// @dev Delete a stream.
    function deleteEntry(uint256 id) external onlyManager {
        require(id < nextId, "ID does not exist");
        Entry memory entry = paymentEntries[id];
        _createEntry(entry.recipient, entry.token, 0, entry.amountDuration, uint40(block.timestamp), entry.endTime);
        emit DeleteEntry(id, block.timestamp, block.number);
    }

    // ===== Internal Functions =====
    function _createEntry(
        address recipient,
        address token,
        uint128 amount,
        uint32 amountDuration,
        uint40 startTime,
        uint40 endTime
    ) internal returns (uint256) {
        uint256 id = nextId;
        nextId = nextId.add(1);
        paymentEntries[id] = Entry(recipient, token, amount, amountDuration, startTime, endTime);
        return id;
    }
}
