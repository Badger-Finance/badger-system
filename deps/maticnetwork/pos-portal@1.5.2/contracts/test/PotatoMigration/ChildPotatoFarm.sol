pragma solidity 0.6.6;

import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";

// This is where potatoes are planted to earn harvest
contract ChildPotatoFarm {
    IERC20 potato;
    mapping(address => uint256) public plantedAmount;

    constructor(address potato_) public {
        potato = IERC20(potato_);
    }

    function plantFor(address user, uint256 amount) external {
        plantedAmount[user] += amount;
        potato.transferFrom(msg.sender, address(this), amount);
    }
}
