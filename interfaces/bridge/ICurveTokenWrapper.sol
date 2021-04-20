// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

interface ICurveTokenWrapper {
    function wrap(address vault) external returns (uint256);

    function unwrap(address vault) external;
}
