// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

interface IClaimZap {
    function claimRewards(
        address[] calldata rewardContracts,
        uint256[] calldata chefIds,
        bool claimCvx,
        bool claimCvxStake,
        bool claimcvxCrv,
        uint256 depositCrvMaxAmount,
        uint256 depositCvxMaxAmount
    ) external;
}
