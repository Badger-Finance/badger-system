pragma solidity 0.6.6;

import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../../child/IStateReceiver.sol";
import "./ChildPotatoFarm.sol";

// This contract receives the deposit of potatoes from pos bridge
// then plants the potatoes for user using custom state sync
contract ChildPotatoMigrator is IStateReceiver {
    IERC20 potato;
    ChildPotatoFarm farm;

    constructor(address potato_, address farm_) public {
        potato = IERC20(potato_);
        farm = ChildPotatoFarm(farm_);
    }

    function onStateReceive(uint256, bytes calldata data) external override {
        (address user, uint256 amount) = abi.decode(data, (address, uint256));
        potato.approve(address(farm), amount);
        farm.plantFor(user, amount);
    }
}
