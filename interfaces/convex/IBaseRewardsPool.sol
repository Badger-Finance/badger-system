// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
interface IBaseRewardsPool {
    function getReward(address _account, bool _claimExtras) external returns (bool);
}
