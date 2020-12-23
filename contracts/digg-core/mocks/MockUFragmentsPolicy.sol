pragma solidity 0.4.24;

import "interfaces/digg/IMock.sol";


contract MockUFragmentsPolicy is IMock {
    
    function rebase() external {
        emit FunctionCalled("UFragmentsPolicy", "rebase", msg.sender);
    }
}
