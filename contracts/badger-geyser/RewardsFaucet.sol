// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/EnumerableSetUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/MathUpgradeable.sol";

/**
    ===== Digg Rewards Faucet =====
    Allow a specified recipient to withdraw DIGG rewards at a rate specified configurable by the admin.
    Define or modify the rate of distribution as: X DIGG shares over Y time
    Adequate DIGG shares must be provided for the distribution

    To facilitate strategies with no other positions, the Digg Faucet can also optionally hold tokens for the recipient

    All mutative functions are pausable by holders of the Pauser role. They can only be unpaused by holders of the Unpauser role.

 */
contract RewardsFaucet is Initializable, AccessControlUpgradeable, PausableUpgradeable, ReentrancyGuardUpgradeable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20Upgradeable for IERC20Upgradeable;

    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant UNPAUSER_ROLE = keccak256("UNPAUSER_ROLE");

    /* ========== STATE VARIABLES ========== */

    IERC20Upgradeable public rewardsToken;
    uint256 public periodFinish;
    uint256 public rewardRate;
    uint256 public rewardsDuration;
    uint256 public lastUpdateTime;
    address public recipient;

    function initialize(address _admin, address _rewardsToken) public initializer whenNotPaused {
        __AccessControl_init();
        __Pausable_init_unchained();
        __ReentrancyGuard_init_unchained();

        _setupRole(DEFAULT_ADMIN_ROLE, _admin);

        rewardsToken = IERC20Upgradeable(_rewardsToken);

        rewardsDuration = 7 days;
    }

    /* ========== VIEWS ========== */

    function lastTimeRewardApplicable() public view returns (uint256) {
        return MathUpgradeable.min(block.timestamp, periodFinish);
    }

    function earned() public view returns (uint256) {
        uint256 timeSinceLastUpdate = lastTimeRewardApplicable().sub(lastUpdateTime);
        return timeSinceLastUpdate.mul(rewardRate);
    }

    function getRewardForDuration() external view returns (uint256) {
        return rewardRate.mul(rewardsDuration);
    }

    /* ========== MUTATIVE FUNCTIONS ========== */
    function getReward() public nonReentrant whenNotPaused {
        _onlyRecipient();

        // Get accumulated rewards and set update time
        uint256 reward = earned();
        lastUpdateTime = lastTimeRewardApplicable();

        if (reward > 0) {
            rewardsToken.safeTransfer(msg.sender, reward);
            emit RewardPaid(msg.sender, reward);
        }
    }

    /* ========== RESTRICTED FUNCTIONS ========== */

    /// @dev Update the reward distribution schedule
    /// @dev Only callable by admin
    /// @param startTimestamp Timestamp to start distribution. If in the past, all "previously" distributed rewards within the range will be immediately claimable.
    /// @param duration Duration over which to distribute the DIGG Shares.
    /// @param totalReward Number of DIGG Shares to distribute within the specified time.
    function notifyRewardAmount(
        uint256 startTimestamp,
        uint256 duration,
        uint256 totalReward
    ) external whenNotPaused {
        _onlyAdmin();
        rewardsDuration = duration;
        rewardRate = totalReward.div(rewardsDuration);

        // Ensure the provided reward amount is not more than the balance in the contract.
        // This keeps the reward rate in the right range, preventing overflows due to
        // very high values of rewardRate in the earned and rewardsPerToken functions;
        // Reward + leftover must be less than 2^256 / 10^18 to avoid overflow.
        uint256 currentBalance = rewardsToken.balanceOf(address(this));
        emit NotifyRewardsAmount(rewardRate, startTimestamp, currentBalance, totalReward, rewardsDuration);
        require(rewardRate <= currentBalance.div(rewardsDuration), "Provided reward too high");

        lastUpdateTime = startTimestamp;
        periodFinish = startTimestamp.add(rewardsDuration);
        emit RewardAdded(totalReward);
        emit RewardsDurationUpdated(rewardsDuration);
    }

    function initializeRecipient(address _recipient) external whenNotPaused {
        _onlyAdmin();
        require(recipient == address(0), "Recipient already set");
        recipient = _recipient;
    }

    function pause() external {
        _onlyAdminOrPauser();
        _pause();
    }

    function unpause() external {
        _onlyAdminOrUnpauser();
        _unpause();
    }

    /* ========== MODIFIERS ========== */
    function _onlyAdmin() internal {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    function _onlyAdminOrPauser() internal {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender) || hasRole(PAUSER_ROLE, msg.sender), "onlyAdminOrPauser");
    }

    function _onlyAdminOrUnpauser() internal {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender) || hasRole(UNPAUSER_ROLE, msg.sender), "onlyAdminOrUnpauser");
    }

    function _onlyRecipient() internal {
        require(msg.sender == recipient, "onlyRecipient");
    }

    /* ========== EVENTS ========== */
    event NotifyRewardsAmount(uint256 rate, uint256 start, uint256 balance, uint256 reward, uint256 duration);

    event RewardAdded(uint256 reward);
    event Staked(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event RewardPaid(address indexed user, uint256 reward);
    event RewardsDurationUpdated(uint256 duration);
    event Recovered(address token, uint256 amount);
}
