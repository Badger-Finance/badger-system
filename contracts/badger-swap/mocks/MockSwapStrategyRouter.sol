// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

contract MockSwapStrategyRouter {
    address public strategy;
    bool public fail;

    constructor(address _strategy, bool _fail) public {
        strategy = _strategy;
        fail = _fail;
    }

    // Always fail by returning an estimated swap amount of 0.
    function optimizeSwap(
        address _from,
        address _to,
        uint256 _amount
    ) external returns (address, uint256) {
        if (fail) {
            return (strategy, 0);
        }
        // Always return configured strategy.
        return (strategy, _amount);
    }
}
