pragma solidity ^0.6.8;

interface IBadgerSettPeak {

    function mint(uint poolId, uint inAmount, bytes32[] calldata merkleProof) external
        returns(uint outAmount);
    
    function approveContractAccess(address account) external;

    function owner() external view returns(address _owner);

    function redeem(uint poolId, uint inAmount) external
        returns (uint outAmount);

<<<<<<< HEAD
    function calcMint(uint poolId, uint inAmount) external view returns(uint bBTC, uint fee);
    function calcRedeem(uint poolId, uint bBtc) external view returns(uint sett, uint fee, uint max);
=======
    function calcMint(uint poolId, uint inAmount)
        external
        view
        returns(uint bBTC, uint fee);
>>>>>>> 760251b525e1ec51b84d3d158b12fe9a0495badd

    function calcRedeem(uint poolId, uint bBtc)
        external
        view
        returns(uint sett, uint fee, uint max);

}