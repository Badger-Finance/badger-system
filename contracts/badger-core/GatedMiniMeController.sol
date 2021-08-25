// SPDX-License-Identifier: LGPL-3.0-only
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "interfaces/badger/IMiniMe.sol";
import "interfaces/erc20/IERC20.sol";

// File contracts/badger-core/GatedMiniMeController.sol

pragma solidity 0.6.12;

/*
    === Gated MiniMe Controller ===
    Limits the functinality of the MiniMe controller address by serving as an intermediate contract.

    The owner maintains the ability to mint and burn tokens from it's own balance, losing the ability to mint and burn to/from arbitrary accounts.
    The MiniMe controller can no longer be changed.
    The owner maintains the ability to claim other tokens sent to the MiniMe contract.

    This contract is designed to be upgradeable, this ability can be removed by transferring the proxyAdmin to 0x0.
    Minting and burning can be permanently removed by the disableMinting() function.

    claimTokens() is designed to be retained. It ability can be removed (along with minting and burning), by burning the owner() address.
*/
contract GatedMiniMeController is OwnableUpgradeable {
    IMiniMe public minime;
    bool public mintingEnabled;
    function initialize(address token_) external initializer {
        __Ownable_init();
        minime = IMiniMe(token_);
        mintingEnabled = true;
    }

    modifier onlyWhenMintingEnabled() {
        require(mintingEnabled == true, "minting disabled");
        _;
    }

    modifier onlyToken() {
        require(msg.sender == address(minime), "a");
        _;
    }

    /// @dev Minting and burning can be permanently disabled by the owner
    function disableMinting() external onlyOwner {
        mintingEnabled = false;
    }

    /// @dev Mint tokens to governance
    function mint(uint256 amount) external onlyOwner onlyWhenMintingEnabled {
        require(minime.generateTokens(owner(), amount), "mint failed");
    }
    
    /// @dev Burn tokens from governance
    function burn(uint256 amount) external onlyOwner onlyWhenMintingEnabled {
        require(minime.destroyTokens(owner(), amount), "burn failed");
    }

    function onTransfer(address _from, address _to, uint256 _amount) external onlyToken returns (bool) {
        return true;
    }

    /**
    * @dev Notifies the controller about an approval allowing the controller to react if desired
    *      Initialization check is implicitly provided by `onlyToken()`.
    * @return False if the controller does not authorize the approval
    */
    function onApprove(address, address, uint) external onlyToken returns (bool) {
        return true;
    }

    /**
    * @dev Called when ether is sent to the MiniMe Token contract
    *      Initialization check is implicitly provided by `onlyToken()`.
    * @return True if the ether is accepted, false for it to throw
    */
    function proxyPayment(address) external payable onlyToken returns (bool) {
        return false;
    }

    /// @dev Claim other tokens
    function claimTokens(address token) external onlyOwner {
        minime.claimTokens(token);
        require(IERC20(token).transfer(owner(), IERC20(token).balanceOf(address(this))), "claim tokens transfer to owner failed");
    }
}