// SPDX-License-Identifier: MIT

pragma solidity >=0.6.0;

interface IRemoteDefender {
    function appproved(address) external view returns (bool);

    function approve(address) external;

    function revoke(address) external;
}
