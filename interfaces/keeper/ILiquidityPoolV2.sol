// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

interface ILiquidityPoolV2 {
    // ===== Write =====
    function deposit(address _token, uint256 _amount) external;
}
