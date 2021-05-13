// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";

/*
    Log information related to rewards
    == Roles ==
    Admins: Set managers
    Managers: Generate logs


*/

contract RewardsLogger is AccessControlUpgradeable {
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");

    struct UnlockSchedule {
        address beneficiary;
        address token;
        uint256 totalAmount;
        uint256 start;
        uint256 end;
        uint256 duration;
    }

    mapping(address => UnlockSchedule[]) public unlockSchedules;

    event UnlockScheduleSet(
        address indexed beneficiary,
        address token,
        uint256 totalAmount,
        uint256 start,
        uint256 end,
        uint256 duration,
        uint256 indexed timestamp,
        uint256 indexed blockNumber
    );
    event UnlockScheduleModified(
        uint256 index,
        address indexed beneficiary,
        address token,
        uint256 totalAmount,
        uint256 start,
        uint256 end,
        uint256 duration,
        uint256 indexed timestamp,
        uint256 indexed blockNumber
    );
    event DiggPegRewards(address indexed beneficiary, uint256 response, uint256 rate, uint256 indexed timestamp, uint256 indexed blockNumber);

    function initialize(address initialAdmin_, address initialManager_) external initializer {
        __AccessControl_init();

        _setupRole(DEFAULT_ADMIN_ROLE, initialAdmin_);
        _setupRole(MANAGER_ROLE, initialManager_);
    }

    modifier onlyManager() {
        require(hasRole(MANAGER_ROLE, msg.sender), "onlyManager");
        _;
    }

    // ===== Permissioned Functions: Manager =====

    function setUnlockSchedule(
        address beneficiary,
        address token,
        uint256 totalAmount,
        uint256 start,
        uint256 end,
        uint256 duration
    ) external onlyManager {
        unlockSchedules[beneficiary].push(UnlockSchedule(beneficiary, token, totalAmount, start, end, duration));
        emit UnlockScheduleSet(beneficiary, token, totalAmount, start, end, duration, block.number, block.timestamp);
    }

    // function modifyUnlockSchedule(
    //     uint256 index,
    //     address beneficiary,
    //     address token,
    //     uint256 totalAmount,
    //     uint256 start,
    //     uint256 end,
    //     uint256 duration
    // ) external {
    //     require(msg.sender == 0xDA25ee226E534d868f0Dd8a459536b03fEE9079b);
    //     unlockSchedules[beneficiary][index] = UnlockSchedule(beneficiary, token, totalAmount, start, end, duration);
    //     emit UnlockScheduleModified(index, beneficiary, token, totalAmount, start, end, duration, block.number, block.timestamp);
    // }

    function setDiggPegRewards(
        address beneficiary,
        uint256 response,
        uint256 rate
    ) external onlyManager {
        emit DiggPegRewards(beneficiary, response, rate, block.number, block.timestamp);
    }

    /// @dev Return all unlock schedules for a given beneficiary
    function getAllUnlockSchedulesFor(address beneficiary) external view returns (UnlockSchedule[] memory) {
        return unlockSchedules[beneficiary];
    }

    /// @dev Return all unlock schedules for a given beneficiary + token
    function getUnlockSchedulesFor(address beneficiary, address token) external view returns (UnlockSchedule[] memory) {
        UnlockSchedule[] memory schedules = unlockSchedules[beneficiary];
        uint256 numMatchingEntries = 0;

        // Determine how many matching entries there are
        for (uint256 i = 0; i < schedules.length; i++) {
            UnlockSchedule memory schedule = schedules[i];
            if (schedule.token == token) {
                numMatchingEntries += 1;
            }
        }

        UnlockSchedule[] memory result = new UnlockSchedule[](numMatchingEntries);
        uint256 resultIndex = 0;

        // Load matching entries into array
        for (uint256 i = 0; i < schedules.length; i++) {
            UnlockSchedule memory schedule = schedules[i];
            if (schedule.token == token) {
                result[resultIndex] = schedule;
                resultIndex += 1;
            }
        }

        return result;
    }
}
