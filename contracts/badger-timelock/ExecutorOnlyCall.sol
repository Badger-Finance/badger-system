pragma solidity >=0.5.0 <0.7.0;

/*
    Gnosis Safe Executor - library wrapping low level calls
    https://github.com/gnosis/safe-contracts/blob/development/contracts/base/Executor.sol

    Ability to execute delegateCall has been removed for security
*/

/// @title Executor - A contract that can execute transactions
/// @author Richard Meissner - <richard@gnosis.pm>

contract ExecutorOnlyCall {
    function execute(
        address to,
        uint256 value,
        bytes memory data,
        uint256 txGas
    ) internal returns (bool success) {
        success = executeCall(to, value, data, txGas);
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
}
