//SPDX-License-Identifier: Unlicense
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";

contract TokenRelease {
    function giveTokensTo(
        IERC20Upgradeable token,
        address recipient,
        uint256 amount
    ) public {
        token.transfer(recipient, amount);
    }
}
