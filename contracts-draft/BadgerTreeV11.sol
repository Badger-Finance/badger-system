// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

import "../../deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "../../deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import "../../interfaces/badger/ICumulativeMultiTokenMerkleDistributor.sol";

/*
    ===== Badger Tree =====
    Unified rewards distribution contract for Badger system

    Access Control:
    - rootProposers: can propose a new state of the system
    - rootValidators: can ratify a state proposed by a rootProposer
    - pausers: can unilaterally pause all write functionality
    - unpausers; can unpause all write functionality
    - managers: can grant and revoke all previously mentioned roles
    - admin: can elect and revoke managers (it can gain control over all roles by electing itself as a manager)

    encodeClaim() convenience can now be used with any account
*/
contract BadgerTreeV11 is Initializable, AccessControlUpgradeable, ICumulativeMultiTokenMerkleDistributor, PausableUpgradeable {
    using SafeMathUpgradeable for uint256;

    struct MerkleData {
        bytes32 root;
        bytes32 contentHash;
        uint256 cycle;
        uint256 startBlock;
        uint256 endBlock;
        uint256 uploadBlock;
        uint256 timestamp;
    }

    // Note: Obselete roles from v1
    // bytes32 public constant ROOT_UPDATER_ROLE = keccak256("ROOT_UPDATER_ROLE");
    // bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");

    bytes32 public constant ROOT_PROPOSER_ROLE = keccak256("ROOT_PROPOSER_ROLE");
    bytes32 public constant ROOT_VALIDATOR_ROLE = keccak256("ROOT_VALIDATOR_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant UNPAUSER_ROLE = keccak256("UNPAUSER_ROLE");
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");

    // Current MerkleData
    uint256 public currentCycle;
    bytes32 public merkleRoot;
    bytes32 public merkleContentHash;

    uint256 public lastPublishTimestamp;
    uint256 public lastPublishBlockNumber;

    // Pending MerkleData
    uint256 public pendingCycle;
    bytes32 public pendingMerkleRoot;
    bytes32 public pendingMerkleContentHash;

    uint256 public lastProposeTimestamp;
    uint256 public lastProposeBlockNumber;

    mapping(address => mapping(address => uint256)) public claimed;
    mapping(address => uint256) public totalClaimed;

    // Current Cycle Block Data
    uint256 public currentCycleStartBlock;
    uint256 public currentCycleEndBlock;

    // Pending Cycle Block Data
    uint256 public pendingCycleStartBlock;
    uint256 public pendingCycleEndBlock;

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

    /// @notice Admins can grant or revoke managers.
    function _onlyAdmin() internal view {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    /// @notice Root updaters can update the root
    function _onlyRootProposer() internal view {
        require(hasRole(ROOT_PROPOSER_ROLE, msg.sender), "onlyRootUpdater");
    }

    function _onlyRootValidator() internal view {
        require(hasRole(ROOT_PROPOSER_ROLE, msg.sender), "onlyRootUpdater");
    }

    function _onlyPauser() internal view {
        require(hasRole(PAUSER_ROLE, msg.sender), "onlyGuardian");
    }

    function _onlyUnpauser() internal view {
        require(hasRole(UNPAUSER_ROLE, msg.sender), "onlyGuardian");
    }

    function getCurrentMerkleData() external view returns (MerkleData memory) {
        return
            MerkleData(
                merkleRoot,
                merkleContentHash,
                currentCycle,
                currentCycleStartBlock,
                currentCycleEndBlock,
                lastProposeBlockNumber,
                lastPublishTimestamp,
            );
    }

    function getPendingMerkleData() external view returns (MerkleData memory) {
        return
            MerkleData(
                pendingMerkleRoot,
                pendingMerkleContentHash,
                pendingCycle,
                pendingCycleStartBlock,
                pendingCycleEndBlock,
                lastProposeBlockNumber,
                lastProposeTimestamp,
            );
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
        address account,
        uint256 index,
        uint256 cycle
    ) public view returns (bytes memory encoded, bytes32 hash) {
        encoded = abi.encodePacked(index, account, cycle, tokens, cumulativeAmounts);
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

        pendingCycleStartBlock = 
        pendingCycleEndBlock = 

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
