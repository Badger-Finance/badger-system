pragma solidity ^0.6.0;
interface IPickleJar {
    function deposit(uint256 _amount) external;
    function withdraw(uint256 _shares) external;
    function token() external view returns (address);
    function getRatio() external view returns (uint256);
}