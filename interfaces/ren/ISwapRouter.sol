//  SPDX-License-Identifier: MIT

pragma solidity >=0.6.0;

// ISwapRouter hides swapping implementation.
interface ISwapRouter {
    function swapTokens(
        address from,
        address to,
        uint256 slippage
    ) external returns (uint256 amount, bool success);

    function estimateSwapAmount(address from, address to) external returns (uint256 amount);
}
