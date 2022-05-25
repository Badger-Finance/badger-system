// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;

interface IProxyAdmin {
    function upgrade(address, address) external;
}
