pragma solidity ^0.6.8;

interface IbyvWbtc {
    function mint(uint inAmount, bytes32[] calldata merkleProof) external returns(uint outAmount);
    function redeem(uint inAmount) external returns (uint outAmount);
    function calcMint(uint inAmount) external view returns(uint bBTC, uint fee);
    function calcRedeem(uint bBtc) external view returns(uint sett, uint fee, uint max);
    function pricePerShare() external view returns (uint);
}
