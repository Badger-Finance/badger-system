// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.6.12;

import "./GatedProxy.sol";

/**
GatedProxy variant with convenience pause function
*/
contract WarRoomGatedProxy is GatedProxy {
    function pause(address destination) public onlyApprovedAccount {
        IPausable(destination).pause();
    }
}
