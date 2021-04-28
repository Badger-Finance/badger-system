//SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;

interface IxSushi {
    function enter(uint256 _amount) external;

    function leave(uint256 _shares) external;
}
