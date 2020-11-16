// SPDX-License-Identifier: MIT

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

/*
    Cumulative Merkle distributor
    Access Control
    - Admins: Can add and remove other admins, can set approved root updaters
    - Root Upgraters: Can freely upload new roots
*/
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import "interfaces/badger/ICumulativeMultiTokenMerkleDistributor.sol";

contract BadgerTree is Initializable, AccessControlUpgradeable, ICumulativeMultiTokenMerkleDistributor, PausableUpgradeable {
    using SafeMathUpgradeable for uint256;

    struct MerkleData {
        bytes32 root;
        bytes32 contentHash;
    }

    /// @dev Track global metadata for tokens as a safeguard against over-spending in the case of invalid root
    struct TokenData {
        uint256 rate; // Expected total distribution rate in tokens-per-second
        uint256 rateOffset; // Offset to apply to expected total available to distribute (useful when changing rate)
        uint256 distributionStart; // Start timestamp for distribution
    }

    bytes32 public constant ROOT_UPDATER_ROLE = keccak256("ROOT_UPDATER_ROLE");
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");

    uint256 public currentCycle;
    mapping(uint256 => bytes32) merkleRoots;
    mapping(uint256 => bytes32) merkleContentHashes;
    mapping(address => TokenData) tokenData;
    mapping(address => mapping(address => uint256)) claimed;

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

    /// @notice Admins can approve new root updaters or admins
    function _onlyAdmin() internal {
        require(hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "onlyAdmin");
    }

    /// @notice Root updaters can update the root
    function _onlyRootUpdater() internal {
        require(hasRole(ROOT_UPDATER_ROLE, msg.sender), "onlyRootUpdater");
    }

    function _onlyGuardian() internal {
        require(hasRole(GUARDIAN_ROLE, msg.sender), "onlyGuardian");
    }

    /// @notice
    function _onlyBelowExpectedLimit(address token) internal {}

    function getCurrentMerkleData() external view returns (MerkleData memory) {
        return MerkleData(merkleRoots[currentCycle], merkleContentHashes[currentCycle]);
    }

    function getMerkleData(uint256 cycle) external view returns (MerkleData memory) {
        return MerkleData(merkleRoots[cycle], merkleContentHashes[cycle]);
    }

    /// @notice Claim accumulated rewards for a set of tokens at a given cycle number
    function claim(
        address[] calldata tokens,
        uint256[] calldata cumulativeAmounts,
        uint256 index,
        uint256 cycle,
        bytes32[] calldata merkleProof
    ) external {
        require(cycle <= currentCycle, "Invalid cycle");
        // Verify the merkle proof.
        bytes32 node = keccak256(abi.encodePacked(index, msg.sender, cycle, tokens, cumulativeAmounts));
        require(MerkleProofUpgradeable.verify(merkleProof, merkleRoots[cycle], node), "Invalid proof");

        // Claim each token
        for (uint256 i = 0; i < tokens.length; i++) {
            _onlyBelowExpectedLimit(tokens[i]);

            uint256 claimable = cumulativeAmounts[i].sub(claimed[msg.sender][tokens[i]]);
            require(claimable > 0, "Excessive claim");

            require(IERC20Upgradeable(tokens[i]).transfer(msg.sender, cumulativeAmounts[i]), "Transfer failed");

            emit Claimed(msg.sender, tokens[i], cumulativeAmounts[i], cycle, now);
        }
    }

    // ====Root Updater Restricted====

    function publishRoot(bytes32 root, bytes32 contentHash) external whenNotPaused {
        _onlyRootUpdater();
        currentCycle = currentCycle.add(1);
        merkleRoots[currentCycle] = root;
        merkleContentHashes[currentCycle] = contentHash;

        emit RootUpdated(currentCycle, root, contentHash, now);
    }

    // ====Guardian Restricted====

    /// @notice Override current cycle, in case of a bad root
    function overrideCurrentCycle(uint256 cycle) external {
        _onlyGuardian();
        currentCycle = cycle;
    }

    /// @notice Pause publishing of new roots
    function pauseUpdates() external {
        _onlyGuardian();
        _pause();
    }

    /// @notice Unpause publishing of new roots
    function unpauseUpdates() external {
        _onlyGuardian();
        _unpause();
    }
}
