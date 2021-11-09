pragma solidity ^0.6.8;

interface IBadgerYearnWbtcPeak {

    function mint(uint inAmount, bytes32[] calldata merkleProof) external
        returns(uint outAmount);
    
    function approveContractAccess(address account) external;

    function owner() external view returns(address _owner);

    function redeem(uint inAmount) external
        returns (uint outAmount);
    
    function calcMint(uint inAmount)
        external
        view
        returns(uint bBTC, uint fee);

    function calcRedeem(uint bBtc)
        external
        view
        returns(uint sett, uint fee, uint max);

}