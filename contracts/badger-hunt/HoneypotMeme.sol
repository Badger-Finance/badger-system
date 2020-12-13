// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";
import "interfaces/meme/IMemeLtd.sol";

contract HoneypotMeme is Initializable {
    using SafeMathUpgradeable for uint256;

    IERC20Upgradeable public token;
    bool public isClaimed;

    IMemeLtd public memeLtd;
    uint256 public honeypot;
    uint256[] public nftIndicies;

    address public constant memeLtdAddress = 0xe4605d46Fd0B3f8329d936a8b258D69276cBa264;

    event Claimed(address account, uint256 amount);

    function initialize(
        IERC20Upgradeable token_,
        uint256 honeypot_,
        uint256[] memory nftIndicies_
    ) public virtual {
        memeLtd = IMemeLtd(memeLtdAddress);
        token = token_;
        honeypot = honeypot_;
        nftIndicies = nftIndicies_;
    }

    function claim() external {
        _verifyRequirements();
        isClaimed = true;
        emit Claimed(msg.sender, honeypot);
        require(token.transfer(msg.sender, honeypot), "honeypot/transfer-failed");
    }

    /// @dev The called must possess all required NFTs, as well as the secret
    function _verifyRequirements() internal {
        require(!isClaimed, "honeypot/is-claimed");
        for (uint256 i = 0; i < nftIndicies.length; i++) {
            require(memeLtd.balanceOf(msg.sender, nftIndicies[i]) > 0, "honeypot/nft-ownership");
        }
    }
}
