// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

import "interfaces/erc20/IERC20.sol";

// Info of each pool.
struct PoolInfo {
    IERC20 lpToken; // Address of LP token contract.
    uint256 allocPoint; // How many allocation points assigned to this pool. SUSHIs to distribute per block.
    uint256 lastRewardBlock; // Last block number that SUSHIs distribution occurs.
    uint256 accSushiPerShare; // Accumulated SUSHIs per share, times 1e12. See below.
}

interface ISushiChef {
    // ===== Write =====

    function deposit(uint256 _pid, uint256 _amount) external;

    function withdraw(uint256 _pid, uint256 _amount) external;

    function add(
        uint256 _allocPoint,
        address _lpToken,
        bool _withUpdate
    ) external;

    function updatePool(uint256 _pid) external;

    // ===== Read =====

    function totalAllocPoint() external view returns (uint256);

    function poolLength() external view returns (uint256);

    function owner() external view returns (address);

    function poolInfo(uint256 _pid) external view returns (PoolInfo memory);

    function pendingSushi(uint256 _pid, address _user) external view returns (uint256);

    function userInfo(uint256 _pid, address _user) external view returns (uint256, uint256);
}
