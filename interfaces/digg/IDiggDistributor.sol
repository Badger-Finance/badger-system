pragma solidity >=0.5.0 <0.8.0;

interface IDiggDistributor {
    
    function rewardsEscrow() external view returns (address);
    function reclaimAllowedTimestamp() external view returns (uint256);
    function isOpen() external view returns (bool);

    function claim(
        uint256 index,
        address account,
        uint256 shares,
        bytes32[] calldata merkleProof
    ) external;

    /// ===== Gated Actions: Owner =====

    /// @notice Transfer unclaimed funds to rewards escrow
    function reclaim() external;

    function pause() external;

    function unpause() external;
    
    function openAirdrop() external;

}
