//SPDX-License-Identifier: Unlicense
pragma solidity 0.6.12;

import "@openzeppelinV3/contracts/token/ERC20/IERC20.sol";
import "@openzeppelinV3/contracts/token/ERC20/ERC20.sol";

contract StakingMock is ERC20 {
    IERC20 stakingToken;
    mapping (address => uint256) staked;

    constructor(IERC20 stakingToken_) ERC20("Staking", "STK") public {
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
