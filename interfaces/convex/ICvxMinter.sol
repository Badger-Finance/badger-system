// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

interface ICvxMinter {
    function reductionPerCliff() external view returns (uint256);
    function totalCliffs() external view returns (uint256);
    function maxSupply() external view returns (uint256);
}