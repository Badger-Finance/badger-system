// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";

interface IGateway {
    function mint(
        bytes32 _pHash,
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external returns (uint256);

    function burn(bytes calldata _to, uint256 _amount) external returns (uint256);
}

interface IGatewayRegistry {
    function getGatewayBySymbol(string calldata _tokenSymbol) external view returns (IGateway);

    function getGatewayByToken(address _tokenAddress) external view returns (IGateway);

    function getTokenBySymbol(string calldata _tokenSymbol) external view returns (IERC20Upgradeable);
}

contract BadgerRenAdapter is Initializable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20Upgradeable for IERC20Upgradeable;

    IERC20Upgradeable renBTC;

    IGatewayRegistry public registry;

    event RecoverStuckRenBTC(uint256 amount);
    event MintRenBTC(uint256 amount);
    event BurnRenBTC(uint256 amount);

    function initialize(address _registry) public {
        registry = IGatewayRegistry(_registry);
        renBTC = registry.getTokenBySymbol("BTC");
    }

    function recoverStuck(
        bytes calldata encoded,
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external {
        // Ensure sender matches sender of original tx.
        uint256 start = encoded.length - 32;
        address sender = abi.decode(encoded[start:], (address));
        require(sender == msg.sender);

        bytes32 pHash = keccak256(encoded);
        uint256 mintedAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);

        emit RecoverStuckRenBTC(mintedAmount);

        renBTC.safeTransfer(msg.sender, mintedAmount);
    }

    function mint(
        // user args
        address payable _renBTCDestination,
        // darknode args
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external {
        // Mint renBTC tokens
        bytes32 pHash = keccak256(abi.encode(_renBTCDestination));
        uint256 mintedAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);

        emit MintRenBTC(mintedAmount);

        renBTC.safeTransfer(_renBTCDestination, mintedAmount);
    }

    function burn(bytes calldata _btcDestination, uint256 _amount) external {
        require(renBTC.balanceOf(address(this)) >= _amount);
        uint256 burnAmount = registry.getGatewayBySymbol("BTC").burn(_btcDestination, _amount);

        emit BurnRenBTC(burnAmount);
    }
}
