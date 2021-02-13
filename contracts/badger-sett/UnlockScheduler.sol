// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "interfaces/badger/ISett.sol";
import "interfaces/badger/IStrategy.sol";
import "interfaces/badger/IBadgerGeyser.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";

contract UnlockScheduler is AccessControlUpgradeable, ReentrancyGuardUpgradeable, PausableUpgradeable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20Upgradeable for IERC20Upgradeable;

    struct UnlockSchedule {
        address geyser;
        address token;
        uint256 amount;
        uint256 durationSec;
        uint256 startTime;
    }

    bytes32 public constant TOKEN_LOCKER_ROLE = keccak256("TOKEN_LOCKER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant UNPAUSER_ROLE = keccak256("UNPAUSER_ROLE");

    function initialize(
        address admin,
        address initialTokenLocker,
        address initialPauser,
        address initialUnpauser
    ) public initializer {
        __AccessControl_init();
        __Pausable_init_unchained();

        _setupRole(DEFAULT_ADMIN_ROLE, admin);
        _setupRole(TOKEN_LOCKER_ROLE, initialTokenLocker);
        _setupRole(PAUSER_ROLE, initialPauser);
        _setupRole(UNPAUSER_ROLE, initialUnpauser);
    }

    /// ===== Modifiers =====
    function _onlyAdmin() internal view {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    function _onlyTokenLocker() internal view {
        require(hasRole(TOKEN_LOCKER_ROLE, msg.sender), "TOKEN_LOCKER_ROLE");
    }

    function _onlyPauser() internal view {
        require(hasRole(PAUSER_ROLE, msg.sender), "onlyPauser");
    }

    function _onlyUnpauser() internal view {
        require(hasRole(UNPAUSER_ROLE, msg.sender), "onlyUnpauser");
    }

    /// @notice Pause all actions
    function pause() external {
        _onlyPauser();
        _pause();
    }

    /// @notice Unpause all actions
    function unpause() external {
        _onlyUnpauser();
        _unpause();
    }

    // ===== Permissioned Functions: Token Locker =====
    function signalTokenLocks(UnlockSchedule[] calldata unlockSchedules) external {
        _onlyTokenLocker();
        for (uint256 i = 0; i < unlockSchedules.length; i++) {
            UnlockSchedule memory schedule = unlockSchedules[i];
            IBadgerGeyser(schedule.geyser).signalTokenLock(schedule.token, schedule.amount, schedule.durationSec, schedule.startTime);
        }
    }
}
