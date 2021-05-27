// SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

// Info of each user.
struct UserInfo {
    uint256 amount; // How many LP tokens the user has provided.
    uint256 rewardDebt; // Reward debt. See explanation below.
    //
    // We do some fancy math here. Basically, any point in time, the amount of CAKEs
    // entitled to a user but is pending to be distributed is:
    //
    //   pending reward = (user.amount * pool.accCakePerShare) - user.rewardDebt
    //
    // Whenever a user deposits or withdraws LP tokens to a pool. Here's what happens:
    //   1. The pool's `accCakePerShare` (and `lastRewardBlock`) gets updated.
    //   2. User receives the pending reward sent to his/her address.
    //   3. User's `amount` gets updated.
    //   4. User's `rewardDebt` gets updated.
}

// Info of each pool.
struct PoolInfo {
    address lpToken; // Address of LP token contract.
    uint256 allocPoint; // How many allocation points assigned to this pool. CAKEs to distribute per block.
    uint256 lastRewardBlock; // Last block number that CAKEs distribution occurs.
    uint256 accCakePerShare; // Accumulated CAKEs per share, times 1e12. See below.
}

interface IPancakeStaking {
    // The CAKE TOKEN!
    function cake() external returns (address);

    // The SYRUP TOKEN!
    function syrup() external returns (address);

    // Dev address.
    function devaddr() external returns (address);

    // CAKE tokens created per block.
    function cakePerBlock() external returns (uint256);

    // Bonus muliplier for early cake makers.
    function BONUS_MULTIPLIER() external returns (uint256);

    // The migrator contract. It has a lot of power. Can only be set through governance (owner).
    function migrator() external returns (address);

    // Info of each pool.
    function poolInfo(uint256 _pid) external view returns (PoolInfo memory);

    // Info of each user that stakes LP tokens.
    function userInfo(uint256 _pid, address _user) external view returns (uint256, uint256);

    // Total allocation poitns. Must be the sum of all allocation points in all pools.
    function totalAllocPoint() external returns (uint256);

    // The block number when CAKE mining starts.
    function startBlock() external returns (uint256);

    function poolLength() external view returns (uint256);

    // Add a new lp to the pool. Can only be called by the owner.
    // XXX DO NOT add the same LP token more than once. Rewards will be messed up if you do.
    function add(
        uint256 _allocPoint,
        address _lpToken,
        bool _withUpdate
    ) external;

    // Update the given pool's CAKE allocation point. Can only be called by the owner.
    function set(
        uint256 _pid,
        uint256 _allocPoint,
        bool _withUpdate
    ) external;

    // Set the migrator contract. Can only be called by the owner.
    function setMigrator(address _migrator) external;

    // Migrate lp token to another lp contract. Can be called by anyone. We trust that migrator contract is good.
    function migrate(uint256 _pid) external;

    // Return reward multiplier over the given _from to _to block.
    function getMultiplier(uint256 _from, uint256 _to) external view returns (uint256);

    // View function to see pending CAKEs on frontend.
    function pendingCake(uint256 _pid, address _user) external view returns (uint256);

    // Update reward variables for all pools. Be careful of gas spending!
    function massUpdatePools() external;

    // Update reward variables of the given pool to be up-to-date.
    function updatePool(uint256 _pid) external;

    // Deposit LP tokens to MasterChef for CAKE allocation.
    function deposit(uint256 _pid, uint256 _amount) external;

    // Withdraw LP tokens from MasterChef.
    function withdraw(uint256 _pid, uint256 _amount) external;

    // Stake CAKE tokens to MasterChef
    function enterStaking(uint256 _amount) external;

    // Withdraw CAKE tokens from STAKING.
    function leaveStaking(uint256 _amount) external;

    // Withdraw without caring about rewards. EMERGENCY ONLY.
    function emergencyWithdraw(uint256 _pid) external;
}
