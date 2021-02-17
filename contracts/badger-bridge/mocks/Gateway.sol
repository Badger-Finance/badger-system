// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts/access/Ownable.sol";
import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "interfaces/bridge/IGateway.sol";

contract MockGatewayRegistry is IGatewayRegistry, Ownable {
    mapping(bytes32 => address) public gateways;
    mapping(bytes32 => address) public tokens;

    constructor() public Ownable() {}

    function getGatewayBySymbol(string calldata _tokenSymbol) external override view returns (IGateway) {
        return IGateway(gateways[keccak256(abi.encodePacked(_tokenSymbol))]);
    }

    function getTokenBySymbol(string calldata _tokenSymbol) external override view returns (IERC20) {
        return IERC20(tokens[keccak256(abi.encodePacked(_tokenSymbol))]);
    }

    // ===== ADMIN =====
    function addGateway(string calldata _tokenSymbol, address _gateway) external onlyOwner {
        gateways[keccak256(abi.encodePacked(_tokenSymbol))] = _gateway;
    }

    function addToken(string calldata _tokenSymbol, address _token) external onlyOwner {
        gateways[keccak256(abi.encodePacked(_tokenSymbol))] = _token;
    }
}

// NB: It's expected that the gateway is loaded w/ the test token during tests.
contract MockGateway is IGateway {
    using SafeERC20 for IERC20;

    address public token;

    constructor(address _token) public {
        token = _token;
    }

    function mint(
        bytes32 _pHash,
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external override returns (uint256) {
        // Just transfer the mint amount to the minter.
        IERC20(token).safeTransfer(msg.sender, _amount);
    }

    function burn(bytes calldata _to, uint256 _amount) external override returns (uint256) {
        // Just transfer the burned amount back to the gateway.
        IERC20(token).safeTransferFrom(msg.sender, address(this), _amount);
    }
}
