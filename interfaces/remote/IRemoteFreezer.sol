// SPDX-License-Identifier: MIT

pragma solidity >=0.6.0;

interface IRemoteFreezer {
    function frozen(address) external view returns (bool);

    function freeze(address) external;

    function unfreeze(address) external;
}
