// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.9.0;

abstract contract IMStableVotingLockup {
    function createLock(uint256 _value, uint256 _unlockTime) external virtual;

    function withdraw() external virtual;

    function exit() external virtual;

    function increaseLockAmount(uint256 _value) external virtual;

    function increaseLockLength(uint256 _unlockTime) external virtual;

    function claimReward() public virtual;

    function earned(address _account) public virtual view returns (uint256);

    // View only ERC20 fns

    function balanceOf(address _owner) public virtual view returns (uint256);

    function balanceOfAt(address _owner, uint256 _blockNumber) public virtual view returns (uint256);

    function totalSupply() public virtual view returns (uint256);

    function totalSupplyAt(uint256 _blockNumber) public virtual view returns (uint256);
}
