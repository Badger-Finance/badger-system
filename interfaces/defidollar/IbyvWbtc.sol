pragma solidity 0.6.11;

import {IERC20} from "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IbyvWbtc is IERC20 {
    function pricePerShare() external view returns (uint);
    function deposit(bytes32[] calldata merkleProof) external;
}