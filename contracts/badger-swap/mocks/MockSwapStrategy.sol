// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

contract MockSwapStrategy {
    using SafeERC20 for IERC20;

    constructor() public {}

    function swapTokens(
        address _from,
        address _to,
        uint256 _amount,
        uint256 _slippage
    ) external returns (uint256 amount) {
        IERC20(_from).safeTransferFrom(msg.sender, address(this), _amount);
        // Always fail.
        revert("always fail swap");
        return 0;
    }

    // Anyone can estimate swap amount as this fn is stateless.
    function estimateSwapAmount(
        address _from,
        address _to,
        uint256 _amount
    ) external returns (uint256) {
        return _amount;
    }

    function _estimateSwapAmount(
        address _from,
        address _to,
        uint256 _amount
    )
        internal
        returns (
            address registry,
            address pool,
            uint256 amount
        )
    {
        return (address(0x0), address(0x0), _amount);
    }
}
