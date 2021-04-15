// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity ^0.6.0;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";

contract ContributorLogger is AccessControlUpgradeable {
    using SafeMathUpgradeable for uint256;
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");

    uint256 public nextId;
    uint256 public lastPaidTimestamp;
    uint256 public firstPaidIndex;

    struct Entry {
        address recipient;
        address token;
        uint256 amount;
        uint256 startTime;
        uint256 endTime;
    }

    mapping(uint256 => Entry) public paymentEntries;

    // ===== Events =====
    event CreateEntry(
        uint256 indexed id,
        address indexed recipient,
        address token,
        uint256 amount,
        uint256 amountDuration,
        uint256 startTime,
        uint256 endTime,
        uint256 indexed timestamp,
        uint256 blockNumber
    );

    event UpdateEntry(
        uint256 indexed id,
        uint256 amount,
        uint256 amountDuration,
        uint256 startTime,
        uint256 endTime,
        uint256 indexed timestamp,
        uint256 blockNumber
    );

    event DeleteEntry(uint256 indexed id, uint256 indexed timestamp, uint256 blockNumber);

    event Checkpoint(uint256 lastPaidTimestamp, uint256 firstPaidIndex);

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
            uint256,
            uint256,
            uint256
        )
    {
        Entry storage entry = paymentEntries[id];
        return (entry.recipient, entry.token, entry.amount, entry.startTime, entry.endTime);
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
        uint256 amount,
        uint256 startTime,
        uint256 endTime
    ) external onlyManager {
        uint256 id = nextId;
        require(startTime >= block.timestamp, "start time cannot be in past");
        uint256 amountDuration = endTime.sub(startTime);
        nextId = nextId.add(1);
        paymentEntries[id] = Entry(recipient, token, amount, startTime, endTime);
        emit CreateEntry(id, recipient, token, amount, amountDuration, startTime, endTime, block.timestamp, block.number);
    }

    /// @dev Update a stream by changing the rate or time parameters.
    /// @dev The recipient and amount cannot be updated on an entry.
    function updateEntry(
        uint256 id,
        uint256 amount,
        uint256 startTime,
        uint256 endTime
    ) external onlyManager {
        require(id < nextId, "ID does not exist");
        uint256 amountDuration = endTime.sub(startTime);
        paymentEntries[id].amount = amount;
        paymentEntries[id].startTime = startTime;
        paymentEntries[id].endTime = endTime;
        emit UpdateEntry(id, amount, amountDuration, startTime, endTime, block.timestamp, block.number);
    }

    /// @dev Delete a stream.
    /// @dev Entries can technically be deleted multiple times without issue, the script will handle this case.
    function deleteEntry(uint256 id) external onlyManager {
        require(id < nextId, "ID does not exist");
        delete paymentEntries[id];
        emit DeleteEntry(id, block.timestamp, block.number);
    }

    /// @dev After pulling payment data for the current period mark where you left off
    function setCheckpoint(uint256 timestamp, uint256 index) external onlyManager {
        lastPaidTimestamp = timestamp;
        firstPaidIndex = index;
        emit Checkpoint(timestamp, index);
    }
}
