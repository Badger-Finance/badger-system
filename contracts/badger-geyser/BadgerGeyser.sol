// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/EnumerableSetUpgradeable.sol";

/**
 * @title Badger Geyser
 @dev Tracks stakes and pledged tokens to be distributed, for use with 
 @dev BadgerTree merkle distribution system. An arbitrary number of tokens to 
 distribute can be specified.
 */

contract BadgerGeyser is Initializable, AccessControlUpgradeable {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using SafeMathUpgradeable for uint256;
    using EnumerableSetUpgradeable for EnumerableSetUpgradeable.AddressSet;

    struct UnlockSchedule {
        uint256 initialLocked;
        uint256 endAtSec;
        uint256 durationSec;
        uint256 startTime;
    }

    uint256 public globalStartTime;

    uint256 public constant MAX_PERCENTAGE = 100;
    bytes32 public constant TOKEN_LOCKER_ROLE = keccak256("TOKEN_LOCKER_ROLE");

    uint256 public totalStaked;

    IERC20Upgradeable internal _stakingToken;
    EnumerableSetUpgradeable.AddressSet distributionTokens;

    mapping(address => uint256) internal _userTotals;
    mapping(address => UnlockSchedule[]) public unlockSchedules;

    event Staked(address indexed user, uint256 amount, uint256 total, uint256 indexed timestamp, uint256 indexed blockNumber, bytes data);
    event Unstaked(address indexed user, uint256 amount, uint256 total, uint256 indexed timestamp, uint256 indexed blockNumber, bytes data);
    event UnlockScheduleSet(address token, uint256 initialLocked, uint256 durationSec, uint256 startTime, uint256 endTime);
    event TokensLocked(
        address indexed token,
        uint256 amount,
        uint256 durationSec,
        uint256 startTime,
        uint256 endTime,
        uint256 indexed timestamp,
        bytes data
    );

    /**
     * @param stakingToken_ The token users deposit as stake.
     * @param initialDistributionToken_ The token users receive as they unstake.
     * @param globalStartTime_ Timestamp after which unlock schedules and staking can begin.
     */
    function initialize(
        IERC20Upgradeable stakingToken_,
        address initialDistributionToken_,
        uint256 globalStartTime_,
        address initialAdmin_,
        address initialTokenLocker_
    ) public initializer {
        __AccessControl_init();

        _setupRole(DEFAULT_ADMIN_ROLE, initialAdmin_);
        _setupRole(TOKEN_LOCKER_ROLE, initialTokenLocker_);

        _stakingToken = stakingToken_;
        distributionTokens.add(initialDistributionToken_);

        globalStartTime = globalStartTime_;
    }

    /// ===== Modifiers =====

    function _onlyAfterStart() internal {
        require(now >= globalStartTime, "BadgerGeyser: Distribution not started");
    }

    function _onlyAdmin() internal {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    function _onlyTokenLocker() internal {
        require(hasRole(TOKEN_LOCKER_ROLE, msg.sender), "onlyTokenLocker");
    }

    /// ===== View Functions =====

    /**
     * @return False. This application does not support staking history.
     */
    function supportsHistory() external pure returns (bool) {
        return false;
    }

    /**
     * @return The token users deposit as stake.
     */
    function getStakingToken() public view returns (IERC20Upgradeable) {
        return _stakingToken;
    }

    /**
     * @return The token users receive as they unstake.
     */
    function getDistributionTokens() public view returns (address[] memory) {
        uint256 numTokens = distributionTokens.length();
        address[] memory tokens = new address[](numTokens);

        for (uint256 i = 0; i < numTokens; i++) {
            tokens[i] = distributionTokens.at(i);
        }

        return tokens;
    }

    function getNumDistributionTokens() public view returns (uint256) {
        return distributionTokens.length();
    }

    /**
     * @param addr The user to look up staking information for.
     * @return The number of staking tokens deposited for addr.
     */
    function totalStakedFor(address addr) public view returns (uint256) {
        return _userTotals[addr];
    }

    /**
     * @return Number of unlock schedules.
     */
    function unlockScheduleCount(address token) public view returns (uint256) {
        return unlockSchedules[token].length;
    }

    function getUnlockSchedulesFor(address token) public view returns (UnlockSchedule[] memory) {
        return unlockSchedules[token];
    }

    /// ===== Public Actions =====

    /**
     * @dev Transfers amount of deposit tokens from the user.
     * @param amount Number of deposit tokens to stake.
     */
    function stake(uint256 amount, bytes calldata data) external {
        _onlyAfterStart();
        _stakeFor(msg.sender, msg.sender, amount);
    }

    /**
     * @dev Transfers amount of deposit tokens from the caller on behalf of user.
     * @param user User address who gains credit for this stake operation.
     * @param amount Number of deposit tokens to stake.
     * @param data Not used.
     */
    function stakeFor(
        address user,
        uint256 amount,
        bytes calldata data
    ) external {
        _onlyAfterStart();
        _stakeFor(msg.sender, user, amount);
    }

    /**
     * @dev Unstakes a certain amount of previously deposited tokens. User also receives their
     * alotted number of distribution tokens.
     * @param amount Number of deposit tokens to unstake / withdraw.
     * @param data Not used.
     */
    function unstake(uint256 amount, bytes calldata data) external {
        _onlyAfterStart();
        _unstakeFor(msg.sender, amount);
    }

    /// ===== Permissioned Actions: Admins =====
    
    function addDistributionToken(address token) external {
        _onlyAdmin();
        distributionTokens.add(token);
    }

    /// ===== Permissioned Actions: Token Lockers =====

    /**
     * @dev This funcion allows the contract owner to pledge more distribution tokens, along
     *      with the associated "unlock schedule". These locked tokens immediately begin unlocking
     *      linearly over the duraction of durationSec timeframe.
     * @param token Token to lock.
     * @param amount Number of distribution tokens to lock. These are transferred from the caller.
     * @param durationSec Length of time to linear unlock the tokens.
     * @param startTime Time to start distribution.
     */
    function signalTokenLock(
        address token,
        uint256 amount,
        uint256 durationSec,
        uint256 startTime
    ) external {
        _onlyTokenLocker();   
        require(startTime >= globalStartTime, "BadgerGeyser: Schedule cannot start before global start time");
        require(distributionTokens.contains(token), "BadgerGeyser: Token not approved by admin");
     
        _signalTokenLock(token, amount, durationSec, startTime);
    }

    /// ===== Internal Implementations =====

    /**
     * @dev Internal implementation of staking methods.
     * @param staker User address who deposits tokens to stake.
     * @param beneficiary User address who gains credit for this stake operation.
     * @param amount Number of deposit tokens to stake.
     */
    function _stakeFor(
        address staker,
        address beneficiary,
        uint256 amount
    ) internal {
        require(amount > 0, "BadgerGeyser: stake amount is zero");
        require(beneficiary != address(0), "BadgerGeyser: beneficiary is zero address");

        // 1. User Accounting
        _userTotals[beneficiary] = _userTotals[beneficiary].add(amount);

        // 2. Global Accounting
        totalStaked = totalStaked.add(amount);

        _stakingToken.safeTransferFrom(staker, address(this), amount);

        emit Staked(beneficiary, amount, totalStakedFor(beneficiary), now, block.number, "");
    }

    /**
     * @dev Unstakes a certain amount of previously deposited tokens. User also receives their
     * alotted number of distribution tokens.
     * @param amount Number of deposit tokens to unstake / withdraw.
     */
    function _unstakeFor(address user, uint256 amount) internal {
        // checks
        require(amount > 0, "BadgerGeyser: unstake amount is zero");
        require(totalStakedFor(user) >= amount, "BadgerGeyser: unstake amount is greater than total user stakes");

        // 1. User Accounting
        _userTotals[user] = _userTotals[user].sub(amount);

        // 2. Global Accounting
        totalStaked = totalStaked.sub(amount);

        // interactions
        _stakingToken.safeTransfer(user, amount);

        emit Unstaked(user, amount, totalStakedFor(user), now, block.number, "");
    }

    function _signalTokenLock(
        address token,
        uint256 amount,
        uint256 durationSec,
        uint256 startTime
    ) internal {

        UnlockSchedule memory schedule;
        schedule.initialLocked = amount;
        schedule.endAtSec = startTime.add(durationSec);
        schedule.durationSec = durationSec;
        schedule.startTime = startTime;
        unlockSchedules[token].push(schedule);

        emit TokensLocked(token, amount, durationSec, startTime, schedule.endAtSec, now, "");
    }
}
