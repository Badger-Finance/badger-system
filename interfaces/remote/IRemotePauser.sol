// SPDX-License-Identifier: MIT

pragma solidity >=0.6.0;

interface IRemotePauser {
    function paused() external view returns (bool);

    function pause() external;

    function unpause() external;
}
