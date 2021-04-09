// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.6.0 <0.7.0;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts/cryptography/MerkleProof.sol";
import "deps/@openzeppelin/contracts/math/SafeMath.sol";
import "interfaces/yearn/GuestlistApi.sol";
import "interfaces/yearn/VaultApi.sol";

/**
 * @notice A basic guest list contract for testing.
 * @dev For a Vyper implementation of this contract containing additional
 * functionality, see https://github.com/banteg/guest-list/blob/master/contracts/GuestList.vy
 * The bouncer can invite arbitrary guests
 * A guest can be added permissionlessly with proof of inclusion in current merkle set
 * The bouncer can change the merkle root at any time
 * Merkle-based permission that has been claimed cannot be revoked permissionlessly.
 * Any guests can be revoked by the bouncer at-will
 * The TVL cap is based on the number of want tokens in the underlying vaults.
 * This can only be made more permissive over time. If decreased, existing TVL is maintained and no deposits are possible until the TVL has gone below the threshold
 * A variant of the yearn AffiliateToken that supports guest list control of deposits
 * A guest list that gates access by merkle root and a TVL cap
 */
contract VipCappedGuestList {
    using SafeMath for uint256;

    address public vault;
    address public bouncer;

    bytes32 public guestRoot;
    uint256 public userDepositCap;

    mapping(address => bool) public guests;

    event ProveInvitation(address indexed account, bytes32 indexed guestRoot);
    event SetGuestRoot(bytes32 indexed guestRoot);
    event SetUserDepositCap(uint256 cap);

    /**
     * @notice Create the test guest list, setting the message sender as
     * `bouncer`.
     * @dev Note that since this is just for testing, you're unable to change
     * `bouncer`.
     */
    constructor(address vault_) public {
        vault = vault_;
        bouncer = msg.sender;
    }

    /**
     * @notice Invite guests or kick them from the party.
     * @param _guests The guests to add or update.
     * @param _invited A flag for each guest at the matching index, inviting or
     * uninviting the guest.
     */
    function setGuests(address[] calldata _guests, bool[] calldata _invited) external {
        require(msg.sender == bouncer, "onlyBouncer");
        _setGuests(_guests, _invited);
    }

    function vaultBalance(address user) public view returns (uint256) {
        return (VaultAPI(vault).balanceOf(user).mul(VaultAPI(vault).pricePerShare())).div((10**VaultAPI(vault).decimals()));
    }

    function remainingDepositAllowed(address user) public view returns (uint256) {
        return userDepositCap - vaultBalance(user);
    }

    /**
     * @notice Permissionly prove an address is included in the current merkle root, thereby granting access
     * @notice Note that the list is designed to ONLY EXPAND in future instances
     * @notice The admin does retain the ability to ban individual addresses
     */
    function proveInvitation(address account, bytes32[] calldata merkleProof) external {
        // Verify Merkle Proof
        bytes32 node = keccak256(abi.encode(account));
        require(MerkleProof.verify(merkleProof, guestRoot, node), "Invalid merkle proof.");

        address[] memory accounts = new address[](1);
        bool[] memory invited = new bool[](1);

        accounts[0] = account;
        invited[0] = true;

        _setGuests(accounts, invited);

        emit ProveInvitation(account, guestRoot);
    }

    /**
     * @notice Set the merkle root to verify invitation proofs against.
     * @notice Note that accounts not included in the root will still be invited if their inviation was previously approved.
     */
    function setGuestRoot(bytes32 guestRoot_) external {
        require(msg.sender == bouncer, "onlyBouncer");
        guestRoot = guestRoot_;

        emit SetGuestRoot(guestRoot);
    }

    /**
     * @notice Set the merkle root to verify invitation proofs against.
     * @notice Note that accounts not included in the root will still be invited if their inviation was previously approved.
     */
    function setUserDepositCap(uint256 cap_) external {
        require(msg.sender == bouncer, "onlyBouncer");
        userDepositCap = cap_;

        emit SetUserDepositCap(userDepositCap);
    }

    /**
     * @notice Check if a guest with a bag of a certain size is allowed into
     * the party.
     * @dev Note that `_amount` isn't checked to keep test setup simple, since
     * from the vault tests' perspective this is a pass/fail call anyway.
     * @param _guest The guest's address to check.
     */
    function authorized(address _guest, uint256 _amount) external view returns (bool) {
        return guests[_guest] && (vaultBalance(_guest) + _amount <= userDepositCap);
    }

    function _setGuests(address[] memory _guests, bool[] memory _invited) internal {
        require(_guests.length == _invited.length);
        for (uint256 i = 0; i < _guests.length; i++) {
            if (_guests[i] == address(0)) {
                break;
            }
            guests[_guests[i]] = _invited[i];
        }
    }
}
