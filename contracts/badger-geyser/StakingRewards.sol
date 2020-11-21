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
 * @title Badger Staking Rewards
 * @dev Gated rewards mechanics for Badger Setts, based on Synthetix * StakingRewards
 */
contract StakingRewards is Initializable, AccessControlUpgradeable, PausableUpgradeable, ReentrancyGuardUpgradeable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20Upgradeable for IERC20Upgradeable;

    /* ========== STATE VARIABLES ========== */

    IERC20Upgradeable public rewardsToken;
    IERC20Upgradeable public stakingToken;
    uint256 public periodFinish;
    uint256 public rewardRate;
    uint256 public rewardsDuration;
    uint256 public lastUpdateTime;
    uint256 public rewardPerTokenStored;

    mapping(address => uint256) public userRewardPerTokenPaid;
    mapping(address => uint256) public rewards;

    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;

    bytes32 public constant APPROVED_STAKER_ROLE = keccak256("APPROVED_STAKER_ROLE");

    function initialize(
        address _admin,
        address _rewardsToken,
        address _stakingToken
    ) public initializer {
        __AccessControl_init();
        __Pausable_init_unchained();
        __ReentrancyGuard_init_unchained();

        _setupRole(DEFAULT_ADMIN_ROLE, _admin);

        rewardsToken = IERC20Upgradeable(_rewardsToken);
        stakingToken = IERC20Upgradeable(_stakingToken);

        rewardsDuration = 7 days;
    }

    /* ========== VIEWS ========== */

    function totalSupply() external view returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) external view returns (uint256) {
        return _balances[account];
    }

    function lastTimeRewardApplicable() public view returns (uint256) {
        return MathUpgradeable.min(block.timestamp, periodFinish);
    }

    function rewardPerToken() public view returns (uint256) {
        if (_totalSupply == 0) {
            return rewardPerTokenStored;
        }
        return rewardPerTokenStored.add(lastTimeRewardApplicable().sub(lastUpdateTime).mul(rewardRate).mul(1e18).div(_totalSupply));
    }

    function earned(address account) public view returns (uint256) {
        return _balances[account].mul(rewardPerToken().sub(userRewardPerTokenPaid[account])).div(1e18).add(rewards[account]);
    }

    function getRewardForDuration() external view returns (uint256) {
        return rewardRate.mul(rewardsDuration);
    }

    /* ========== MUTATIVE FUNCTIONS ========== */

    function stake(uint256 amount) external nonReentrant whenNotPaused updateReward(msg.sender) {
        _onlyApprovedStaker();
        require(amount > 0, "Cannot stake 0");
        _totalSupply = _totalSupply.add(amount);
        _balances[msg.sender] = _balances[msg.sender].add(amount);
        stakingToken.safeTransferFrom(msg.sender, address(this), amount);
        emit Staked(msg.sender, amount);
    }

    function withdraw(uint256 amount) public nonReentrant updateReward(msg.sender) {
        require(amount > 0, "Cannot withdraw 0");
        _totalSupply = _totalSupply.sub(amount);
        _balances[msg.sender] = _balances[msg.sender].sub(amount);
        stakingToken.safeTransfer(msg.sender, amount);
        emit Withdrawn(msg.sender, amount);
    }

    function getReward() public nonReentrant updateReward(msg.sender) {
        uint256 reward = rewards[msg.sender];
        if (reward > 0) {
            rewards[msg.sender] = 0;
            rewardsToken.safeTransfer(msg.sender, reward);
            emit RewardPaid(msg.sender, reward);
        }
    }

    function exit() external {
        withdraw(_balances[msg.sender]);
        getReward();
    }

    /* ========== RESTRICTED FUNCTIONS ========== */

    function notifyRewardAmount(uint256 reward) external updateReward(address(0)) {
        _onlyAdmin();
        if (block.timestamp >= periodFinish) {
            rewardRate = reward.div(rewardsDuration);
        } else {
            uint256 remaining = periodFinish.sub(block.timestamp);
            uint256 leftover = remaining.mul(rewardRate);
            rewardRate = reward.add(leftover).div(rewardsDuration);
        }

        // Ensure the provided reward amount is not more than the balance in the contract.
        // This keeps the reward rate in the right range, preventing overflows due to
        // very high values of rewardRate in the earned and rewardsPerToken functions;
        // Reward + leftover must be less than 2^256 / 10^18 to avoid overflow.
        uint256 balance = rewardsToken.balanceOf(address(this));
        emit Test(rewardRate, balance, reward, rewardsDuration);
        require(rewardRate <= balance.div(rewardsDuration), "Provided reward too high");

        lastUpdateTime = block.timestamp;
        periodFinish = block.timestamp.add(rewardsDuration);
        emit RewardAdded(reward);
    }

    // Added to support recovering LP Rewards from other systems such as BAL to be distributed to holders
    function recoverERC20(address tokenAddress, uint256 tokenAmount) external {
        _onlyAdmin();
        // Cannot recover the staking token or the rewards token
        require(tokenAddress != address(stakingToken) && tokenAddress != address(rewardsToken), "Cannot withdraw the staking or rewards tokens");
        IERC20Upgradeable(tokenAddress).safeTransfer(getRoleMember(DEFAULT_ADMIN_ROLE, 0), tokenAmount);
        emit Recovered(tokenAddress, tokenAmount);
    }

    function setRewardsDuration(uint256 _rewardsDuration) external {
        _onlyAdmin();
        require(block.timestamp > periodFinish, "Previous rewards period must be complete before changing the duration for the new period");
        rewardsDuration = _rewardsDuration;
        emit RewardsDurationUpdated(rewardsDuration);
    }

    function pause() external {
        _onlyAdmin();
        _pause();
    }

    function unpause() external {
        _onlyAdmin();
        _unpause();
    }

    /* ========== MODIFIERS ========== */

    modifier updateReward(address account) {
        rewardPerTokenStored = rewardPerToken();
        lastUpdateTime = lastTimeRewardApplicable();
        if (account != address(0)) {
            rewards[account] = earned(account);
            userRewardPerTokenPaid[account] = rewardPerTokenStored;
        }
        _;
    }

    function _onlyAdmin() internal {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    function _onlyApprovedStaker() internal {
        require(hasRole(APPROVED_STAKER_ROLE, msg.sender), "onlyApprovedStaker");
    }

    /* ========== EVENTS ========== */
    event Test(uint256 rate, uint256 balance, uint256 reward, uint256 duration);

    event RewardAdded(uint256 reward);
    event Staked(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event RewardPaid(address indexed user, uint256 reward);
    event RewardsDurationUpdated(uint256 newDuration);
    event Recovered(address token, uint256 amount);
}
