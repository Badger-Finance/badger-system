//SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.7.0;

contract Executor {
    function execute(
        address to,
        uint256 value,
        bytes memory data,
        uint256 operation,
        uint256 txGas
    ) internal returns (bool success) {
        if (operation == 0) success = executeCall(to, value, data, txGas);
        else if (operation == 1) success = executeDelegateCall(to, data, txGas);
        else success = false;
    }

    function executeCall(
        address to,
        uint256 value,
        bytes memory data,
        uint256 txGas
    ) internal returns (bool success) {
        // solium-disable-next-line security/no-inline-assembly
        assembly {
            success := call(txGas, to, value, add(data, 0x20), mload(data), 0, 0)
        }
    }

    function executeDelegateCall(
        address to,
        bytes memory data,
        uint256 txGas
    ) internal returns (bool success) {
        // solium-disable-next-line security/no-inline-assembly
        assembly {
            success := delegatecall(txGas, to, add(data, 0x20), mload(data), 0, 0)
        }
    }
}
