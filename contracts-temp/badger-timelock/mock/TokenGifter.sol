//SPDX-License-Identifier: Unlicense
pragma solidity 0.6.12;

import "@openzeppelinV3/contracts/token/ERC20/IERC20.sol";

contract TokenGifter {
    function requestTransfer(IERC20 token, uint256 amount) public {
        token.transfer(msg.sender, amount);
    }
}
