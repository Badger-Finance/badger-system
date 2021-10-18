// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

interface ICvxRewardsPool {
    //balance
    function balanceOf(address _account) external view returns (uint256);

    //withdraw to a convex tokenized deposit
    function withdraw(uint256 _amount, bool _claim) external;

    function withdrawAll(bool _claim) external;

    //withdraw directly to curve LP token
    function withdrawAndUnwrap(uint256 _amount, bool _claim) external returns (bool);

    //claim rewards
    function getReward(bool _stake) external;

    //stake a convex tokenized deposit
    function stake(uint256 _amount) external;

    //stake a convex tokenized deposit for another address(transfering ownership)
    function stakeFor(address _account, uint256 _amount) external returns (bool);

    function rewards(address _account) external view returns (uint256);

    function earned(address _account) external view returns (uint256);
}
