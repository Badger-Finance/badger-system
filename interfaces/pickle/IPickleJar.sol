//SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;

interface IPickleJar {
    function deposit(uint256 _amount) external;

    function withdraw(uint256 _shares) external;

    function withdrawAll() external;

    function token() external view returns (address);

    function balanceOf(address account) external view returns (uint256);

    function getRatio() external view returns (uint256);
}
