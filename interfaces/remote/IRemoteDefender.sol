// SPDX-License-Identifier: MIT

pragma solidity >=0.6.0;

interface IRemoteDefender {
    function approved(address account) external view returns (bool);

    function approve(address account) external;

    function revoke(address account) external;

    function approveFor(address account, address target) external;

    function revoke(address account, address target) external;

    function frozen(address account) external view returns (bool);

    function freeze(address account) external;

    function unfreeze(address account) external;
}
