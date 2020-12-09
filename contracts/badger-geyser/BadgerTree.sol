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

    /// @notice Admins can approve new root updaters or admins
    function _onlyAdmin() internal view {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    /// @notice Root updaters can update the root
    function _onlyRootUpdater() internal view {
        require(hasRole(ROOT_UPDATER_ROLE, msg.sender), "onlyRootUpdater");
    }

    function _onlyGuardian() internal view {
        require(hasRole(GUARDIAN_ROLE, msg.sender), "onlyGuardian");
    }

    function getCurrentMerkleData() external view returns (MerkleData memory) {
        return MerkleData(merkleRoot, merkleContentHash, lastPublishTimestamp, lastProposeBlockNumber);
    }

    function getPendingMerkleData() external view returns (MerkleData memory) {
        return MerkleData(pendingMerkleRoot, pendingMerkleContentHash, lastProposeTimestamp, lastProposeBlockNumber);
    }

    function hasPendingRoot() external view returns (bool) {
        return pendingCycle == currentCycle.add(1);
    }

    function getClaimedFor(address user, address[] memory tokens) public view returns (address[] memory, uint256[] memory) {
        uint256[] memory userClaimed = new uint256[](tokens.length);
        for (uint256 i = 0; i < tokens.length; i++) {
            userClaimed[i] = claimed[user][tokens[i]];
        }
        return (tokens, userClaimed);
    }

    function encodeClaim(
        address[] calldata tokens,
        uint256[] calldata cumulativeAmounts,
        uint256 index,
        uint256 cycle
    ) public view returns (bytes memory encoded, bytes32 hash) {
        encoded = abi.encodePacked(index, msg.sender, cycle, tokens, cumulativeAmounts);
        hash = keccak256(encoded);
    }

    /// @notice Claim accumulated rewards for a set of tokens at a given cycle number
    function claim(
        address[] calldata tokens,
        uint256[] calldata cumulativeAmounts,
        uint256 index,
        uint256 cycle,
        bytes32[] calldata merkleProof
    ) external whenNotPaused {
        require(cycle == currentCycle, "Invalid cycle");

        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encodePacked(index, msg.sender, cycle, tokens, cumulativeAmounts));
        require(MerkleProofUpgradeable.verify(merkleProof, merkleRoot, node), "Invalid proof");

        // Claim each token
        for (uint256 i = 0; i < tokens.length; i++) {
            uint256 claimable = cumulativeAmounts[i].sub(claimed[msg.sender][tokens[i]]);

            require(claimable > 0, "Excessive claim");

            claimed[msg.sender][tokens[i]] = claimed[msg.sender][tokens[i]].add(claimable);

            require(claimed[msg.sender][tokens[i]] == cumulativeAmounts[i], "Claimed amount mismatch");
            require(IERC20Upgradeable(tokens[i]).transfer(msg.sender, claimable), "Transfer failed");

            emit Claimed(msg.sender, tokens[i], claimable, cycle, now, block.number);
        }
    }

    // ===== Root Updater Restricted =====

    /// @notice Propose a new root and content hash, which will be stored as pending until approved
    function proposeRoot(
        bytes32 root,
        bytes32 contentHash,
        uint256 cycle
    ) external whenNotPaused {
        _onlyRootUpdater();
        require(cycle == currentCycle.add(1), "Incorrect cycle");

        pendingCycle = cycle;
        pendingMerkleRoot = root;
        pendingMerkleContentHash = contentHash;
        lastProposeTimestamp = now;
        lastProposeBlockNumber = block.number;

        emit RootProposed(cycle, pendingMerkleRoot, pendingMerkleContentHash, now, block.number);
    }

    /// ===== Guardian Restricted =====

    /// @notice Approve the current pending root and content hash
    function approveRoot(
        bytes32 root,
        bytes32 contentHash,
        uint256 cycle
    ) external {
        _onlyGuardian();
        require(root == pendingMerkleRoot, "Incorrect root");
        require(contentHash == pendingMerkleContentHash, "Incorrect content hash");
        require(cycle == pendingCycle, "Incorrect cycle");

        currentCycle = cycle;
        merkleRoot = root;
        merkleContentHash = contentHash;
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
}
