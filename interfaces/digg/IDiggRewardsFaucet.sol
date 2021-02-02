// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.8.0;

interface IDiggRewardsFaucet {
    /* ========== VIEWS ========== */

    function lastTimeRewardApplicable() external view returns (uint256);

    function earned() external view returns (uint256);

    function getRewardForDuration() external view returns (uint256);

    function periodFinish() external view returns (uint256);

    function rewardRate() external view returns (uint256);

    function rewardsDuration() external view returns (uint256);

    function lastUpdateTime() external view returns (uint256);

    function recipient() external view returns (address);

    /* ========== MUTATIVE FUNCTIONS ========== */
    function getReward() external;

    /* ========== RESTRICTED FUNCTIONS ========== */

    /// @dev Update the reward distribution schedule
    /// @dev Only callable by admin
    /// @param startTimestamp Timestamp to start distribution. If in the past, all "previously" distributed rewards within the range will be immediately claimable.
    /// @param duration Duration over which to distribute the DIGG Shares.
    /// @param rewardInShares Number of DIGG Shares to distribute within the specified time.
    function notifyRewardAmount(
        uint256 startTimestamp,
        uint256 duration,
        uint256 rewardInShares
    ) external;

    function initializeRecipient(address _recipient) external;

    function pause() external;

    function unpause() external;
}
