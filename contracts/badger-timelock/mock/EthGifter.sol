//SPDX-License-Identifier: Unlicense
pragma solidity 0.6.12;

contract EthGifter {
    function requestEth(uint256 amount) public payable {
        msg.sender.transfer(amount);
    }

    receive() external payable {}
}
