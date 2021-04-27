// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import "interfaces/badger/ICumulativeMultiTokenMerkleDistributor.sol";
import "interfaces/digg/IDigg.sol";

contract BadgerTreeV2 is Initializable, AccessControlUpgradeable, ICumulativeMultiTokenMerkleDistributor, PausableUpgradeable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;

    struct MerkleData {
        bytes32 root;
        bytes32 contentHash;
        uint256 timestamp;
        uint256 publishBlock;
        uint256 startBlock;
        uint256 endBlock;
    }

    bytes32 public constant ROOT_PROPOSER_ROLE = keccak256("ROOT_PROPOSER_ROLE");
    bytes32 public constant ROOT_VALIDATOR_ROLE = keccak256("ROOT_VALIDATOR_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant UNPAUSER_ROLE = keccak256("UNPAUSER_ROLE");

    address private constant DIGG_ADDRESS = 0x798D1bE841a82a273720CE31c822C61a67a601C3;

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

    uint256 public lastPublishStartBlock;
    uint256 public lastPublishEndBlock;

    uint256 public lastProposeStartBlock;
    uint256 public lastProposeEndBlock;

    mapping(uint256 => bytes32) merkleRoots; // Mapping of historical merkle roots. Other information about each cycle such as content hash and start/end blocks are not used on-chain and can be found in historical events

    function initialize(
        address admin,
        address initialProposer,
        address initialValidator
    ) public initializer {
        __AccessControl_init();
        __Pausable_init_unchained();

        _setupRole(DEFAULT_ADMIN_ROLE, admin); // The admin can edit all role permissions
        _setupRole(ROOT_PROPOSER_ROLE, initialProposer); // The admin can edit all role permissions
        _setupRole(ROOT_VALIDATOR_ROLE, initialValidator); // The admin can edit all role permissions
    }

    /// ===== Modifiers =====

    /// @notice Admins can approve new root updaters or admins
    function _onlyAdmin() internal view {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    /// @notice Root updaters can update the root
    function _onlyRootProposer() internal view {
        require(hasRole(ROOT_PROPOSER_ROLE, msg.sender), "onlyRootProposer");
    }

    function _onlyRootValidator() internal view {
        require(hasRole(ROOT_VALIDATOR_ROLE, msg.sender), "onlyRootValidator");
    }

    function _onlyPauser() internal view {
        require(hasRole(PAUSER_ROLE, msg.sender), "onlyPauser");
    }

    function _onlyUnpauser() internal view {
        require(hasRole(UNPAUSER_ROLE, msg.sender), "onlyUnpauser");
    }

    function getCurrentMerkleData() external view returns (MerkleData memory) {
        return
            MerkleData(merkleRoot, merkleContentHash, lastPublishTimestamp, lastPublishBlockNumber, lastPublishStartBlock, lastPublishEndBlock);
    }

    function getPendingMerkleData() external view returns (MerkleData memory) {
        return
            MerkleData(
                pendingMerkleRoot,
                pendingMerkleContentHash,
                lastProposeTimestamp,
                lastProposeBlockNumber,
                lastProposeStartBlock,
                lastProposeEndBlock
            );
    }

    function getMerkleRootFor(uint256 cycle) public view returns (bytes32) {
        return merkleRoots[cycle];
    }

    function hasPendingRoot() external view returns (bool) {
        return pendingCycle == currentCycle.add(1);
    }

    /// @dev Return true if account has outstanding claims in any token from the given input data
    function isClaimAvailableFor(
        address user,
        address[] memory tokens,
        uint256[] memory cumulativeAmounts
    ) public view returns (bool) {
        for (uint256 i = 0; i < tokens.length; i++) {
            uint256 userClaimable = cumulativeAmounts[i].sub(claimed[user][tokens[i]]);
            if (userClaimable > 0) {
                return true;
            }
        }
        return false;
    }

    /// @dev Get the number of tokens claimable for an account, given a list of tokens and latest cumulativeAmounts data
    function getClaimableFor(
        address user,
        address[] memory tokens,
        uint256[] memory cumulativeAmounts
    ) public view returns (address[] memory, uint256[] memory) {
        uint256[] memory userClaimable = new uint256[](tokens.length);
        for (uint256 i = 0; i < tokens.length; i++) {
            userClaimable[i] = cumulativeAmounts[i].sub(_getClaimed(user, tokens[i]));
        }
        return (tokens, userClaimable);
    }

    /// @dev Get the cumulative number of tokens claimed for an account, given a list of tokens
    function getClaimedFor(address user, address[] memory tokens) public view returns (address[] memory, uint256[] memory) {
        uint256[] memory userClaimed = new uint256[](tokens.length);
        for (uint256 i = 0; i < tokens.length; i++) {
            userClaimed[i] = claimed[user][tokens[i]];
        }
        return (tokens, userClaimed);
    }

    /// @dev Utility function to encode a merkle tree node
    function encodeClaim(
        address[] calldata tokens,
        uint256[] calldata cumulativeAmounts,
        address account,
        uint256 index,
        uint256 cycle
    ) public pure returns (bytes memory encoded, bytes32 hash) {
        encoded = abi.encode(index, account, cycle, tokens, cumulativeAmounts);
        hash = keccak256(encoded);
    }

    /// @notice Claim specifiedrewards for a set of tokens at a given cycle number
    /// @notice Can choose to skip certain tokens by setting amount to claim to zero for that token index
    function claim(
        address[] calldata tokens,
        uint256[] calldata cumulativeAmounts,
        uint256 index,
        uint256 cycle,
        bytes32[] calldata merkleProof,
        uint256[] calldata amountsToClaim
    ) external whenNotPaused {
        // require(cycle <= currentCycle, "Invalid cycle");
        require(cycle == currentCycle, "Invalid cycle");
        _verifyClaimProof(tokens, cumulativeAmounts, index, cycle, merkleProof);

        bool claimedAny = false; // User must claim at least 1 token by the end of the function

        // Claim each token
        for (uint256 i = 0; i < tokens.length; i++) {
            // Run claim and register claimedAny if a claim occurs
            if (_tryClaim(msg.sender, cycle, tokens[i], cumulativeAmounts[i], amountsToClaim[i])) {
                claimedAny = true;
            }
        }

        // If no tokens were claimed, revert
        if (claimedAny == false) {
            revert("No tokens to claim");
        }
    }

    // ===== Root Updater Restricted =====

    /// @notice Propose a new root and content hash, which will be stored as pending until approved
    function proposeRoot(
        bytes32 root,
        bytes32 contentHash,
        uint256 cycle,
        uint256 startBlock,
        uint256 endBlock
    ) external whenNotPaused {
        _onlyRootProposer();
        require(cycle == currentCycle.add(1), "Incorrect cycle");
        // require(startBlock == lastPublishEndBlock.add(1), "Incorrect start block");

        pendingCycle = cycle;
        pendingMerkleRoot = root;
        pendingMerkleContentHash = contentHash;
        lastProposeStartBlock = startBlock;
        lastProposeEndBlock = endBlock;

        lastProposeTimestamp = now;
        lastProposeBlockNumber = block.number;

        emit RootProposed(cycle, pendingMerkleRoot, pendingMerkleContentHash, startBlock, endBlock, now, block.number);
    }

    /// ===== Guardian Restricted =====

    /// @notice Approve the current pending root and content hash
    function approveRoot(
        bytes32 root,
        bytes32 contentHash,
        uint256 cycle,
        uint256 startBlock,
        uint256 endBlock
    ) external {
        _onlyRootValidator();
        require(root == pendingMerkleRoot, "Incorrect root");
        require(contentHash == pendingMerkleContentHash, "Incorrect content hash");
        require(cycle == pendingCycle, "Incorrect cycle");

        require(startBlock == lastProposeStartBlock, "Incorrect cycle start block");
        require(endBlock == lastProposeEndBlock, "Incorrect cycle end block");

        currentCycle = cycle;

        merkleRoots[cycle] = root;
        merkleRoot = root;

        merkleContentHash = contentHash;
        lastPublishStartBlock = startBlock;
        lastPublishEndBlock = endBlock;

        lastPublishTimestamp = now;
        lastPublishBlockNumber = block.number;

        emit RootUpdated(currentCycle, root, contentHash, startBlock, endBlock, now, block.number);
    }

    /// @notice Pause publishing of new roots
    function pause() external {
        _onlyPauser();
        _pause();
    }

    /// @notice Unpause publishing of new roots
    function unpause() external {
        _onlyUnpauser();
        _unpause();
    }

    /// ===== Internal Helper Functions =====

    function _verifyClaimProof(
        address[] calldata tokens,
        uint256[] calldata cumulativeAmounts,
        uint256 index,
        uint256 cycle,
        bytes32[] calldata merkleProof
    ) internal view {
        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encode(index, msg.sender, cycle, tokens, cumulativeAmounts));
        // require(MerkleProofUpgradeable.verify(merkleProof, getMerkleRootFor(cycle), node), "Invalid proof");
        require(MerkleProofUpgradeable.verify(merkleProof, merkleRoot, node), "Invalid proof");
    }

    function _getClaimed(address account, address token) internal view returns (uint256) {
        return claimed[account][token];
    }

    function _setClaimed(
        address account,
        address token,
        uint256 amount
    ) internal {
        claimed[account][token] = amount;
    }

    function _tryClaim(
        address account,
        uint256 cycle,
        address token,
        uint256 cumulativeClaimable,
        uint256 toClaim
    ) internal returns (bool claimAttempted) {
        // If none claimable for token or none specifed to claim, skip this token
        if (cumulativeClaimable == 0 || toClaim == 0) {
            return false;
        }

        uint256 claimedBefore = _getClaimed(account, token);
        uint256 claimable = cumulativeClaimable.sub(claimedBefore);

        // If none claimable, don't attempt to claim
        if (claimable == 0) {
            return false;
        }

        require(claimable > 0, "None available to claim"); // This is reduntant, it is kept to ward off evil claimers.
        require(toClaim <= claimable, "Excessive claim");

        uint256 claimedAfter = claimedBefore.add(toClaim);
        _setClaimed(account, token, claimedAfter);

        require(claimedAfter <= cumulativeClaimable, "Invariant: cumulative claimed > cumulative claimable");
        IERC20Upgradeable(token).safeTransfer(account, _parseValue(token, toClaim));

        emit Claimed(account, token, toClaim, cycle, now, block.number);
        return true;
    }

    /// @dev Determine how many tokens to distribute based on cumulativeAmount
    /// @dev Parse share values for rebasing tokens according to their logic
    /// @dev Return normal ERC20 values directly
    /// @dev Currently handles the DIGG special case
    function _parseValue(address token, uint256 amount) internal view returns (uint256) {
        if (token == DIGG_ADDRESS) {
            return IDigg(token).sharesToFragments(amount);
        } else {
            return amount;
        }
    }

    /// @dev test function to get cycle to starting point
    function setCycle(uint256 x) public {
        _onlyAdmin();
        currentCycle = x;
    }
}
