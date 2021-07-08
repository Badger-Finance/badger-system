// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.8.0;

interface IChainlinkForwarder {
    function getThePrice() external returns (int256);
}
