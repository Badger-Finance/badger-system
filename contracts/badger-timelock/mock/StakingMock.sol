//SPDX-License-Identifier: Unlicense
pragma solidity 0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";

contract StakingMock is ERC20Upgradeable {
    IERC20Upgradeable stakingToken;
    mapping(address => uint256) staked;

    function initialize(IERC20Upgradeable stakingToken_) public initializer {
        __ERC20_init("Staking", "STK");
        stakingToken = stakingToken_;
    }

    // @notice Take staking token from sender
    function stake(uint256 amount) public {
        staked[msg.sender] = staked[msg.sender].add(amount);
        stakingToken.transferFrom(msg.sender, address(this), amount);
    }

    // @notice Return staking token to sender with equivalent of distributed token, minted on demand
    function unstake(uint256 amount) public {
        staked[msg.sender] = staked[msg.sender].add(amount);
        stakingToken.transfer(msg.sender, amount);
        mint(msg.sender, amount);
    }

    function mint(address recipient, uint256 amount) internal {
        _mint(recipient, amount);
    }
}
