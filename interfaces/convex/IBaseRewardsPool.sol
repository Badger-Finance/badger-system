// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

interface IBaseRewardsPool {
    //balance
    function balanceOf(address _account) external view returns (uint256);

    //withdraw to a convex tokenized deposit
    function withdraw(uint256 _amount, bool _claim) external returns (bool);

    //withdraw directly to curve LP token
    function withdrawAndUnwrap(uint256 _amount, bool _claim) external returns (bool);

    //claim rewards
    function getReward() external returns (bool);

    //stake a convex tokenized deposit
    function stake(uint256 _amount) external returns (bool);

    //stake a convex tokenized deposit for another address(transfering ownership)
    function stakeFor(address _account, uint256 _amount) external returns (bool);

    function getReward(address _account, bool _claimExtras) external returns (bool);

    function rewards(address _account) external view returns (uint256);

    function earned(address _account) external view returns (uint256);

    function stakingToken() external view returns (address);
}
