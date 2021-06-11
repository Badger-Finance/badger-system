pragma solidity ^0.6.8;

interface IBadgerSettPeak {

    function mint(uint poolId, uint inAmount, bytes32[] calldata merkleProof) external
        returns(uint outAmount);
    
    function approveContractAccess(address account) external;

    function owner() external view returns(address _owner);

    function redeem(uint poolId, uint inAmount) external
        returns (uint outAmount);


}