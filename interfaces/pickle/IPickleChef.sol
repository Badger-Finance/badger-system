//SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;

interface IPickleChef {
    function deposit(uint256 _pid, uint256 _amount) external;

    function withdraw(uint256 _pid, uint256 _amount) external;

    function poolInfo(uint256 _pid)
        external
        view
        returns (
            address,
            uint256,
            uint256,
            uint256
        );

    function pendingPickle(uint256 _pid, address _user) external view returns (uint256);

    function userInfo(uint256 _pid, address _user) external view returns (uint256, uint256);
}
