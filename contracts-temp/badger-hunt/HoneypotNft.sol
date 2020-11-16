// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "deps/@openzeppelin/contracts/math/SafeMath.sol";

/*
    Badger Honeypot: Meme NFTs

    Requirements to claim:
    * Know secret
    * Own all from a list of NFTs
*/
contract HoneypotNft is Initializable {
    using SafeMath for uint256;

    IERC20 public token;
    uint256 public claimsStart;
    bool public isClaimed;

    IERC721[] public nftContracts;
    uint256[] public nftIndicies;

    bytes32 public secretHash;

    event Claimed(address account, uint256 amount);

    function initialize(
        IERC20 token_,
        uint256 claimsStart_,
        IERC721[] memory nftContracts_,
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
