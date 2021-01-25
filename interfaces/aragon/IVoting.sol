// SPDX-License-Identifier: MIT

// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.8.0;

interface IVoting {
    function vote(
        uint256 _voteId,
        bool _supports,
        bool _executesIfDecided
    ) external payable;
}
