// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.8.0;

interface ICurveVotingEscrow {
    function locked(address arg0)
        external
        view
        returns (int128 amount, uint256 end);

    function locked__end(address _addr) external view returns (uint256);

    function create_lock(uint256 _value, uint256 _unlock_time) external;

    function increase_amount(uint256 _value) external;

    function increase_unlock_time(uint256 _unlock_time) external;

    function withdraw() external;
}