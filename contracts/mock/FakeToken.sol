// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";

contract FakeToken is ERC20Upgradeable {
    function initialize(address holder, uint256 balance) public initializer {
        __ERC20_init("Mock Interest-Bearing Bitcoin", "mockibBTC");
            // _mint(holder, balance);
    }
}
