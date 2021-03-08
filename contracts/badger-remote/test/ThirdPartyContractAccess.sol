// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;

import "interfaces/badger/ISett.sol";

/*
    ThirdPartyContractAccess is a test contract for simulating third party contract access to our API.
 */
contract ThirdPartyContractAccess {
    address public sett;

    constructor(address _sett) public {
        sett = _sett;
    }

    // Test third party access paths for Sett methods (if authorized).
    function depositAll() external {
        ISett(sett).depositAll();
    }

    function withdrawAll() external {
        ISett(sett).withdrawAll();
    }

    function deposit(uint256 _amount) external {
        ISett(sett).deposit(_amount);
    }

    function withdraw(uint256 _amount) external {
        ISett(sett).withdraw(_amount);
    }
}
