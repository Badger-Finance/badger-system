// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

import "../../deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import "../../interfaces/badger/ICumulativeMultiTokenMerkleDistributor.sol";

contract BadgerTree is Initializable, AccessControlUpgradeable, ICumulativeMultiTokenMerkleDistributor, PausableUpgradeable {
    using SafeMathUpgradeable for uint256;

    struct MerkleData {
        bytes32 root;
        bytes32 contentHash;
        uint256 timestamp;
        uint256 blockNumber;
    }

    bytes32 public constant ROOT_UPDATER_ROLE = keccak256("ROOT_UPDATER_ROLE");
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");

    uint256 public currentCycle;
    bytes32 public merkleRoot;
    bytes32 public merkleContentHash;
    uint256 public lastPublishTimestamp;
    uint256 public lastPublishBlockNumber;

    uint256 public pendingCycle;
    bytes32 public pendingMerkleRoot;
    bytes32 public pendingMerkleContentHash;
    uint256 public lastProposeTimestamp;
    uint256 public lastProposeBlockNumber;

    mapping(address => mapping(address => uint256)) public claimed;
    mapping(address => uint256) public totalClaimed;

    struct ExpectedClaimable {
        uint256 base;
        uint256 rate;
        uint256 startTime;
    }

    struct Claim {
        address[] tokens;
        uint256[] cumulativeAmounts;
        address account;
        uint256 index;
        uint256 cycle;
    }

    mapping(address => ExpectedClaimable) public expectedClaimable;

    event ExpectedClaimableSet(address indexed token, uint256 base, uint256 rate);

    uint256 public constant ONE_DAY = 86400; // One day in seconds

    function initialize(
        address admin,
        address initialUpdater,
        address initialGuardian
    ) public initializer {
        __AccessControl_init();
        __Pausable_init_unchained();

        _setupRole(DEFAULT_ADMIN_ROLE, admin); // The admin can edit all role permissions
        _setupRole(ROOT_UPDATER_ROLE, initialUpdater);
        _setupRole(GUARDIAN_ROLE, initialGuardian);
    }

    /// ===== Modifiers =====

    /// @notice Admins can approve or revoke new root updaters, guardians, or admins
    function _onlyAdmin() internal view {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    /// @notice Root updaters can update the root
    function _onlyRootUpdater() internal view {
        require(hasRole(ROOT_UPDATER_ROLE, msg.sender), "onlyRootUpdater");
    }

    /// @notice Guardians can approve the root
    function _onlyGuardian() internal view {
        require(hasRole(GUARDIAN_ROLE, msg.sender), "onlyGuardian");
    }

    // ===== Read Functions =====

    function getCurrentMerkleData() external view returns (MerkleData memory) {
        return MerkleData(merkleRoot, merkleContentHash, lastPublishTimestamp, lastProposeBlockNumber);
    }

    function getPendingMerkleData() external view returns (MerkleData memory) {
        return MerkleData(pendingMerkleRoot, pendingMerkleContentHash, lastProposeTimestamp, lastProposeBlockNumber);
    }

    function hasPendingRoot() external view returns (bool) {
        return pendingCycle == currentCycle.add(1);
    }

    function getClaimedFor(address user, address[] memory tokens) external view returns (address[] memory, uint256[] memory) {
        uint256[] memory userClaimed = new uint256[](tokens.length);
        for (uint256 i = 0; i < tokens.length; i++) {
            userClaimed[i] = claimed[user][tokens[i]];
        }
        return (tokens, userClaimed);
    }

    function getExpectedTotalClaimable(address token) public view returns (uint256) {
        uint256 sinceStart = now.sub(expectedClaimable[token].startTime);
        uint256 rateEmissions = expectedClaimable[token].rate.mul(sinceStart).div(ONE_DAY);
        return expectedClaimable[token].base.add(rateEmissions);
    }

    /// @dev Convenience function for encoding claim data
    function encodeClaim(Claim calldata claim) external pure returns (bytes memory encoded, bytes32 hash) {
        encoded = abi.encodePacked(claim.index, claim.account, claim.cycle, claim.claim.tokens, claim.cumulativeAmounts);
        hash = keccak256(encoded);
    }

    // ===== Public Actions =====

    /// @notice Claim accumulated rewards for a set of tokens at a given cycle number
    /// @dev The primary reason to claim partially is to not claim for tokens that are of 'dust' values, saving gas for those token transfers
    /// @dev Amounts are made partial as well for flexibility. Perhaps a rewards program could rewards leaving assets unclaimed.
    function claim(
        address[] calldata tokensToClaim,
        uint256[] calldata amountsToClaim,
        Claim calldata claim,
        bytes32[] calldata merkleProof
    ) external whenNotPaused {
        require(cycle == currentCycle, "Invalid cycle");
        _verifyClaimProof(claim, merkleProof);

        // Claim each token
        for (uint256 i = 0; i < claim.tokensToClaim.length; i++) {
            _tryClaim(claim.tokensToClaim[i], account, amountsToClaim[i], claim.cumulativeAmounts[i]);
        }
    }

    // ===== Root Updater Restricted =====

    /// @notice Propose a new root and content hash, which will be stored as pending until approved
    function proposeRoot(
        bytes32 root,
        bytes32 contentHash,
        uint256 cycle,
        uint256 blockNumber
    ) external whenNotPaused {
        _onlyRootUpdater();
        require(cycle == currentCycle.add(1), "Incorrect cycle");

        pendingCycle = cycle;
        pendingMerkleRoot = root;
        pendingMerkleContentHash = contentHash;
        pendingBlockNumber = blockNumber;

        lastProposeTimestamp = now;
        lastProposeBlockNumber = block.number;

        emit RootProposed(cycle, pendingMerkleRoot, pendingMerkleContentHash, now, block.number);
    }

    /// ===== Guardian Restricted =====

    /// @notice Approve the current pending root and content hash
    function approveRoot(
        bytes32 root,
        bytes32 contentHash,
        uint256 cycle,
        uint256 blockNumber
    ) external {
        _onlyGuardian();
        require(root == pendingMerkleRoot, "Incorrect root");
        require(contentHash == pendingMerkleContentHash, "Incorrect content hash");
        require(cycle == pendingCycle, "Incorrect cycle");

        currentCycle = cycle;
        merkleRoot = root;
        merkleContentHash = contentHash;
        publishBlockNumber = blockNumber;

        lastPublishTimestamp = now;
        lastPublishBlockNumber = block.number;

        emit RootUpdated(currentCycle, root, contentHash, now, block.number);
    }

    /// @notice Pause publishing of new roots
    function pause() external {
        _onlyGuardian();
        _pause();
    }

    /// @notice Unpause publishing of new roots
    function unpause() external {
        _onlyGuardian();
        _unpause();
    }

    // ===== Admin Restricted =====

    /// @notice Set the expected release rate for a given token
    /// @param token Asset address
    /// @param base Base amount of token expected to be releasable.
    /// @param rate Daily rate of expected emissions
    /// @dev When updating emission schedule, set the base to the the cumulative claimable from the previous rate, and set the new rate as indended.
    /// @dev The startTime will be the current time, tracking the new rate into the future.
    function setExpectedClaimable(
        address token,
        uint256 base,
        uint256 rate
    ) external {
        _onlyAdmin();
        expectedClaimable[token] = ExpectedClaimable(base, rate, now);
        ExpectedClaimableSet(token, base, rate);
    }

    function initializeTotalClaimed(address token, uint256 claimed) {
        _onlyAdmin();
        require(totalClaimed[token] == 0, "Already has value");
        totalClaimed[token] = claimed;
    }

    // ===== Internal helper functions =====
    function _verifyClaimProof(
        address[] calldata tokens,
        uint256[] calldata cumulativeAmounts,
        uint256 index,
        uint256 cycle,
        bytes32[] calldata merkleProof
    ) internal {
        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encodePacked(index, msg.sender, cycle, tokens, cumulativeAmounts));
        require(MerkleProofUpgradeable.verify(merkleProof, merkleRoot, node), "Invalid proof");
    }

    function _getClaimed(address token, address account) internal returns (uint256) {
        return claimed[account][token];
    }

    function _setClaimed(
        address token,
        address account,
        unit256 amount
    ) internal {
        claimed[account][token] = claimed[account][token].add(amount);
    }

    function _addTotalClaimed(address token, uint256 amount) internal {
        totalClaimed[token] = totalClaimed[token].add(amount);
    }

    function _verifyTotalClaimed(address token) internal {
        require(totalClaimed[token] <= _getExpectedTotalClaimable(token));
    }

    function _tryClaim(
        address token,
        address account,
        uint256 amount,
        uint256 maxCumulativeAmount
    ) internal {
        uint256 claimed = _getClaimed(token, account);
        uint256 afterClaim = _setClaimed(token, account, claimed.add(amount));

        require(afterClaim <= maxCumulativeAmount, "Excessive claim");

        IERC20Upgradeable(tokens[i]).safeTransfer(account, amount);

        _addTotalClaimed(amount);
        _verifyTotalClaimed(token, amount);

        emit Claimed(account, token, amount, cycle, now, block.number);
    }
}
