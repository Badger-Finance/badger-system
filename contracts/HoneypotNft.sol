// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC721/IERC721Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";

/*
    Badger Honeypot: Meme NFTs

    Requirements to claim:
    * Know secret
    * Own all from a list of NFTs
*/
contract HoneypotNft is Initializable {
    using SafeMathUpgradeable for uint256;

    IERC20Upgradeable public token;
    uint256 public claimsStart;
    bool public isClaimed;

    IERC721Upgradeable[] public nftContracts;
    uint256[] public nftIndicies;

    bytes32 public secretHash;

    event Claimed(address account, uint256 amount);

    function initialize(
        IERC20Upgradeable token_,
        uint256 claimsStart_,
        IERC721Upgradeable[] memory nftContracts_,
        uint256[] memory nftIndicies_
    ) public virtual {
        token = token_;
        claimsStart = claimsStart_;
    }

    function claim(uint256 amount, bytes memory secret) external virtual {
        _verifyRequirements(secret);
        isClaimed = true;
        emit Claimed(msg.sender, amount);
        require(token.transfer(msg.sender, amount), "honeypot/transfer-failed");
    }

    /// @dev The called must possess all required NFTs, as well as the secret
    function _verifyRequirements(bytes memory secret) internal virtual {
        require(!isClaimed, "honeypot/is-claimed");
        require(keccak256(abi.encode(secret)) == secretHash, "honeypot/secret-hash");

        for (uint256 i = 0; i < nftContracts.length; i++) {
            require(nftContracts[i].ownerOf(nftIndicies[i]) == msg.sender, "honeypot/nft-ownership");
        }
    }
}
