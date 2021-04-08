// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts/access/Ownable.sol";
import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "interfaces/bridge/IBridgeVault.sol";

contract MockVault is ERC20 {
    using SafeERC20 for IERC20;

    address public token;

    constructor(
        string memory _name,
        string memory _symbol,
        address _token
    ) public ERC20(_name, _symbol) {
        token = _token;
    }

    // NB: Normally we'd track ppfs but this is just for testing so we skip that.
    // Underlying token and vault token are 1:1.
    function deposit(uint256 _amount) external {
        IERC20(token).safeTransferFrom(msg.sender, address(this), _amount);
        _mint(msg.sender, _amount);
    }

    function withdraw(uint256 _amount) external {
        IERC20(token).safeTransfer(msg.sender, _amount);
        _burn(msg.sender, _amount);
    }
}
