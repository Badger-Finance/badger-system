// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/EnumerableSetUpgradeable.sol";

/**
 * @title Harvestable Geyser
 * @dev A smart-contract based mechanism to distribute tokens over time, inspired loosely by
 *      Compound and Uniswap. Based on the Ampleforth implementation.
 *      (https://github.com/ampleforth/token-geyser/)
 *
 *      Distribution tokens are added to a locked pool in the contract and become unlocked over time
 *      according to a once-configurable unlock schedule. Once unlocked, they are available to be
 *      claimed by users.
 *
 *      A user may deposit tokens to accrue ownership share over the unlocked pool. This owner share
 *      is a function of the number of tokens deposited as well as the length of time deposited.
 *      Specifically, a user's share of the currently-unlocked pool equals their "deposit-seconds"
 *      divided by the global "deposit-seconds".
 *
 *      More background and motivation available at:
 *      https://github.com/ampleforth/RFCs/blob/master/RFCs/rfc-1.md
 */
contract BadgerGeyser is Initializable, AccessControlUpgradeable {
    using SafeMathUpgradeable for uint256;
    using EnumerableSetUpgradeable for EnumerableSetUpgradeable.AddressSet;

    event Staked(address indexed user, uint256 amount, uint256 total, uint256 indexed timestamp, uint256 indexed blockNumber, bytes data);
    event Unstaked(address indexed user, uint256 amount, uint256 total, uint256 indexed timestamp, uint256 indexed blockNumber, bytes data);

    event TokensLocked(
        address indexed token,
        uint256 amount,
        uint256 durationSec,
        uint256 startTime,
        uint256 endTime,
        uint256 indexed timestamp,
        bytes data
    );

    address public bonusLogic;
    uint256 public globalStartTime;

    bytes32 public constant TOKEN_LOCKER_ROLE = keccak256("TOKEN_LOCKER_ROLE");

    event UnlockScheduleSet(address token, uint256 initialLocked, uint256 durationSec, uint256 startTime, uint256 endTime);

    //
    // Global accounting state
    //
    uint256 public totalStakingShares;
    uint256 public initialSharesPerToken;

    IERC20Upgradeable internal _stakingToken;
    EnumerableSetUpgradeable.AddressSet distributionTokens;

    // Caches aggregated values from the User->Stake[] map to save computation.
    // If lastAccountingTimestampSec is 0, there's no entry for that user.
    struct UserTotals {
        uint256 stakingShares;
    }

    // Aggregated staking values per user
    mapping(address => UserTotals) internal _userTotals;

    //
    // Locked/Unlocked Accounting state
    //
    struct UnlockSchedule {
        uint256 initialLocked;
        uint256 endAtSec;
        uint256 durationSec;
        uint256 startTime;
    }

    mapping(address => UnlockSchedule[]) public unlockSchedules;

    //
    // Founder Lock state
    //
    uint256 public constant MAX_PERCENTAGE = 100;
    uint256 public founderRewardPercentage = 0; //0% - 100%
    address public founderRewardAddress;

    /**
     * @param stakingToken_ The token users deposit as stake.
     * @param initialDistributionToken_ The token users receive as they unstake.
     * @param initialSharesPerToken_ Number of shares to mint per staking token on first stake.
     * @param globalStartTime_ Timestamp after which unlock schedules and staking can begin.
     * @param founderRewardAddress_ Recipient address of founder rewards.
     * @param founderRewardPercentage_ Pecentage of rewards claimed to be distributed for founder address.
     */
    function initialize(
        IERC20Upgradeable stakingToken_,
        address initialDistributionToken_,
        uint256 initialSharesPerToken_,
        uint256 globalStartTime_,
        address founderRewardAddress_,
        uint256 founderRewardPercentage_
    ) public initializer {
        // The founder reward must be some fraction of the max. (i.e. <= 100%)
        require(founderRewardPercentage_ <= MAX_PERCENTAGE, "HarvestableGeyser: founder reward too high");

        // If no period is desired, instead set startBonus = 100%
        // and bonusPeriod to a small value like 1sec.
        require(initialSharesPerToken_ > 0, "HarvestableGeyser: initialSharesPerToken is zero");

        __AccessControl_init();

        globalStartTime = globalStartTime_;

        initialSharesPerToken = initialSharesPerToken_;
        founderRewardPercentage = founderRewardPercentage_;
        founderRewardAddress = founderRewardAddress_;
    }

    function _onlyAfterStart() internal {
        require(now >= globalStartTime, "BadgerGeyser: Distribution not started");
    }

    function _onlyAdmin() internal {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    function _onlyTokenLocker() internal {
        require(hasRole(TOKEN_LOCKER_ROLE, msg.sender), "onlyTokenLocker");
    }

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

    function addDistributionToken(address token) external {
        _onlyAdmin();
        distributionTokens.add(token);
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
        require(totalStakingShares == 0 || totalStaked() > 0, "BadgerGeyser: Invalid state. Staking shares exist, but no staking tokens do");

        uint256 mintedStakingShares = (totalStakingShares > 0)
            ? totalStakingShares.mul(amount).div(totalStaked())
            : amount.mul(initialSharesPerToken);
        require(mintedStakingShares > 0, "BadgerGeyser: Stake amount is too small");

        // 1. User Accounting
        UserTotals storage totals = _userTotals[beneficiary];
        totals.stakingShares = totals.stakingShares.add(mintedStakingShares);

        // 2. Global Accounting
        totalStakingShares = totalStakingShares.add(mintedStakingShares);
        // Already set in updateAccounting()
        // _lastAccountingTimestampSec = now;

        // interactions
        require(_stakingToken.transferFrom(staker, address(this), amount), "BadgerGeyser: staking transfer failed");

        emit Staked(beneficiary, amount, totalStakedFor(beneficiary), now, block.number, "");
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

    /**
     * @dev Unstakes a certain amount of previously deposited tokens. User also receives their
     * alotted number of distribution tokens.
     * @param amount Number of deposit tokens to unstake / withdraw.
     * @return totalReward The total number of distribution tokens rewarded.
     * @return userReward The total number of distribution tokens rewarded.
     * @return founderReward The total number of distribution tokens rewarded.
     */
    function _unstakeFor(address user, uint256 amount)
        internal
        virtual
        returns (
            uint256 totalReward,
            uint256 userReward,
            uint256 founderReward
        )
    {
        // checks
        require(amount > 0, "BadgerGeyser: unstake amount is zero");
        require(totalStakedFor(user) >= amount, "BadgerGeyser: unstake amount is greater than total user stakes");
        uint256 stakingSharesToBurn = totalStakingShares.mul(amount).div(totalStaked());
        require(stakingSharesToBurn > 0, "BadgerGeyser: Unable to unstake amount this small");

        // 1. User Accounting
        UserTotals storage totals = _userTotals[user];

        totals.stakingShares = totals.stakingShares.sub(stakingSharesToBurn);
        totalStakingShares = totalStakingShares.sub(stakingSharesToBurn);

        // interactions
        require(_stakingToken.transfer(user, amount), "BadgerGeyser: unstake transfer failed");

        emit Unstaked(user, amount, totalStakedFor(user), now, block.number, "");

        require(totalStakingShares == 0 || totalStaked() > 0, "BadgerGeyser: Error unstaking. Staking shares exist, but no staking tokens do");
    }

    /**
     * @param addr The user to look up staking information for.
     * @return The number of staking tokens deposited for addr.
     */
    function totalStakedFor(address addr) public view returns (uint256) {
        return totalStakingShares > 0 ? totalStaked().mul(_userTotals[addr].stakingShares).div(totalStakingShares) : 0;
    }

    /**
     * @return The total number of deposit tokens staked globally, by all users.
     */
    function totalStaked() public view returns (uint256) {
        return totalStakingShares;
    }

    /**
     * @return Number of unlock schedules.
     */
    function unlockScheduleCount(address token) public view returns (uint256) {
        return unlockSchedules[token].length;
    }

    /**
     * @dev This funcion allows the contract owner to pledge more distribution tokens, along
     *      with the associated "unlock schedule". These locked tokens immediately begin unlocking
     *      linearly over the duraction of durationSec timeframe.
     * @param token Token to lock.
     * @param amount Number of distribution tokens to lock. These are transferred from the caller.
     * @param durationSec Length of time to linear unlock the tokens.
     * @param startTime Time to start distribution.
     */
    function lockTokens(
        address token,
        uint256 amount,
        uint256 durationSec,
        uint256 startTime
    ) external {
        _lockTokens(token, amount, durationSec, startTime);
    }

    function _lockTokens(
        address token,
        uint256 amount,
        uint256 durationSec,
        uint256 startTime
    ) internal {
        require(startTime >= globalStartTime, "BadgerGeyser: schedule cannot start before global start time");

        UnlockSchedule memory schedule;
        schedule.initialLocked = amount;
        schedule.endAtSec = startTime.add(durationSec);
        schedule.durationSec = durationSec;
        schedule.startTime = startTime;
        unlockSchedules[token].push(schedule);

        emit TokensLocked(token, amount, durationSec, startTime, schedule.endAtSec, now, "");
    }
}
