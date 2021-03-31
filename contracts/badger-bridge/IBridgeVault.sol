// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IBridgeVault is IERC20 {
    function deposit(uint256 amount) external;

    function withdraw(uint256 shares) external;
}
