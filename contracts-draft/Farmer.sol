// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

/*
    Utility functions for staking in farms that conform to the stardard SynthetixRewards interface
*/
contract Farmer is Initializable, AccessControlUpgradeable {

    bytes32 public constant APPROVED_FARM = keccak256("APPROVED_FARM");

    function harvest(address farm) {

    }

    function stake(address farm, uint256 amount) {

    }

}
