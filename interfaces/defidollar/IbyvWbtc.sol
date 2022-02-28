<<<<<<< HEAD
pragma solidity ^0.6.8;

interface IbyvWbtc {
    function mint(uint inAmount, bytes32[] calldata merkleProof) external returns(uint outAmount);
    function redeem(uint inAmount) external returns (uint outAmount);
    function calcMint(uint inAmount) external view returns(uint bBTC, uint fee);
    function calcRedeem(uint bBtc) external view returns(uint sett, uint fee, uint max);
    function pricePerShare() external view returns (uint);
}
=======
pragma solidity 0.6.11;

import {IERC20} from "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IbyvWbtc is IERC20 {
    function pricePerShare() external view returns (uint);
    function deposit(bytes32[] calldata merkleProof) external;
}
>>>>>>> 760251b5 (update defidollar interfaces)
