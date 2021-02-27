// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

/*
    RemoteFreezer handles reporting of frozen state and 
    freezing of addresses  by the owner.
 */
contract RemoteFreezer is OwnableUpgradeable {
    mapping(address => bool) private _frozen;

    function initialize() public initializer {
        __Ownable_init();
    }

    function frozen(address account) external view returns (bool) {
        return _frozen[account];
    }

    function freeze(address account) external onlyOwner {
        _frozen[account] = true;
    }

    function unfreeze(address account) external onlyOwner {
        _frozen[account] = false;
    }
}
