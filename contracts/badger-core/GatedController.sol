// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "interfaces/badger/IMiniMe.sol";
/*
    -enableTransfers() is disabled permanently
*/
contract GatedMiniMeController is OwnableUpgradeable {
    IMiniMe public minime;
    function initialize(address token_) external {
        __Ownable_init();
        minime = IMiniMe(token_);
    }    

    /// @dev Mint tokens to governance
    function mint(uint256 amount) external onlyOwner {
        require(minime.generateTokens(owner(), amount), "mint failed");
    }
    
    /// @dev Burn tokens from governance
    function burn(uint256 amount) external onlyOwner {
        require(minime.destroyTokens(owner(), amount), "burn failed");
    }

    /// @dev Claim other tokens
    function claimTokens(address token) external onlyOwner {
        minime.claimTokens(token);
    }
}
