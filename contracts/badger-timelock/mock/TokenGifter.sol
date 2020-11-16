//SPDX-License-Identifier: Unlicense
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";

contract TokenGifter {
    function requestTransfer(IERC20Upgradeable token, uint256 amount) public {
        token.transfer(msg.sender, amount);
    }
}
