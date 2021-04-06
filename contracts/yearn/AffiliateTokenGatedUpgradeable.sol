// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "./BaseWrapperUpgradeable.sol";

import "interfaces/yearn/VaultApi.sol";
import "interfaces/yearn/GuestlistApi.sol";

/**
    == Access Control ==
    The Affiliate is the governance of the wrapper. It has 
    The manager is a representative set by governance to manage moderately sensitive operations. In this case, the sole permission is unpausing the contract.
    The guardian is a representative that has pausing rights (but not unpausing). This is intended to allow for a fast response in the event of an active exploit or to prevent exploit in the case of a discovered vulnerability.

    More Events
    Each action emits events to faciliate easier logging and monitoring
 */
contract AffiliateTokenGatedUpgradeable is ERC20Upgradeable, BaseWrapperUpgradeable, PausableUpgradeable {
    /// @notice The EIP-712 typehash for the contract's domain
    bytes32 public constant DOMAIN_TYPEHASH = keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    bytes32 public DOMAIN_SEPARATOR;

    /// @notice The EIP-712 typehash for the permit struct used by the contract
    bytes32 public constant PERMIT_TYPEHASH = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");

    uint256 constant MAX_BPS = 10000;

    /// @notice A record of states for signing / validating signatures
    mapping(address => uint256) public nonces;

    address public affiliate;

    address public pendingAffiliate;

    // ===== GatedUpgradeable additional parameters =====

    GuestListAPI public guestList;

    address public manager;

    address public guardian;

    uint256 public withdrawalFee;

    modifier onlyAffiliate() {
        require(msg.sender == affiliate);
        _;
    }

    event PendingAffiliate(address affiliate);
    event AcceptAffiliate(address affiliate);
    event SetGuardian(address guardian);
    event SetManager(address manager);
    event UpdateGuestList(address guestList);
    event Deposit(address indexed account, uint256 amount);
    event Withdraw(address indexed account, uint256 amount);
    event WithdrawalFee(address indexed recipient, uint256 amount);
    event Mint(address indexed account, uint256 shares);
    event Burn(address indexed account, uint256 shares);

    function initialize(
        address _token,
        address _registry,
        string memory name,
        string memory symbol,
        address _guardian
    ) external initializer {
        _BaseWrapperUpgradeable_init(_token, _registry);
        __ERC20_init(name, symbol);

        DOMAIN_SEPARATOR = keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256(bytes(name)), keccak256(bytes("1")), _getChainId(), address(this)));
        affiliate = msg.sender;
        guardian = _guardian;
        _setupDecimals(uint8(ERC20Upgradeable(address(token)).decimals()));

        emit AcceptAffiliate(affiliate);
        emit SetGuardian(guardian);
    }

    function _getChainId() internal view returns (uint256) {
        uint256 chainId;
        assembly {
            chainId := chainid()
        }
        return chainId;
    }

    // ===== Access Control Setters =====
    function setAffiliate(address _affiliate) external onlyAffiliate {
        pendingAffiliate = _affiliate;

        emit PendingAffiliate(pendingAffiliate);
    }

    function acceptAffiliate() external {
        require(msg.sender == pendingAffiliate);
        affiliate = msg.sender;

        emit AcceptAffiliate(affiliate);
    }

    function setGuardian(address _guardian) external onlyAffiliate {
        guardian = _guardian;

        emit SetGuardian(guardian);
    }

    function setManager(address _manager) external onlyAffiliate {
        manager = _manager;

        emit SetManager(manager);
    }

    function setGuestList(address _guestList) external onlyAffiliate {
        guestList = GuestListAPI(_guestList);
        emit UpdateGuestList(_guestList);
    }

    function _shareValue(uint256 numShares) internal view returns (uint256) {
        uint256 totalShares = totalSupply();

        if (totalShares > 0) {
            return totalVaultBalance(address(this)).mul(numShares).div(totalShares);
        } else {
            return numShares;
        }
    }

    function pricePerShare() external view returns (uint256) {
        return totalVaultBalance(address(this)).mul(10**uint256(decimals())).div(totalSupply());
    }

    function _sharesForValue(uint256 amount) internal view returns (uint256) {
        // total wrapper assets before deposit (assumes deposit already occured)
        uint256 totalWrapperAssets = totalVaultBalance(address(this));

        if (totalWrapperAssets > 0) {
            return totalSupply().mul(amount).div(totalWrapperAssets);
        } else {
            return amount;
        }
    }

    function deposit() external whenNotPaused returns (uint256) {
        return deposit(uint256(-1)); // Deposit everything
    }

    function deposit(uint256 amount) public whenNotPaused returns (uint256 deposited) {
        if (address(guestList) != address(0)) {
            require(guestList.authorized(msg.sender, amount), "guest-list-authorization");
        }

        deposited = _deposit(msg.sender, address(this), amount, true); // `true` = pull from `msg.sender`
        uint256 shares = _sharesForValue(deposited); // NOTE: Must be calculated after deposit is handled
        _mint(msg.sender, shares);

        emit Deposit(msg.sender, deposited);
        emit Mint(msg.sender, shares);
    }

    function withdraw() external whenNotPaused returns (uint256) {
        return withdraw(balanceOf(msg.sender));
    }

    function withdraw(uint256 shares) public whenNotPaused returns (uint256 withdrawn) {
        _burn(msg.sender, shares);
        withdrawn = _withdraw(address(this), msg.sender, _shareValue(shares), true); // `true` = withdraw from `bestVault`

        // emit Withdraw(msg.sender, toReceiver);
        // emit WithdrawalFee(affiliate, fee);
        emit Burn(msg.sender, shares);
    }

    function migrate() external onlyAffiliate whenNotPaused returns (uint256) {
        return _migrate(address(this));
    }

    function migrate(uint256 amount) external onlyAffiliate whenNotPaused returns (uint256) {
        return _migrate(address(this), amount);
    }

    function migrate(uint256 amount, uint256 maxMigrationLoss) external onlyAffiliate whenNotPaused returns (uint256) {
        return _migrate(address(this), amount, maxMigrationLoss);
    }

    /**
     * @notice Triggers an approval from owner to spends
     * @param owner The address to approve from
     * @param spender The address to be approved
     * @param amount The number of tokens that are approved (2^256-1 means infinite)
     * @param deadline The time at which to expire the signature
     * @param v The recovery byte of the signature
     * @param r Half of the ECDSA signature pair
     * @param s Half of the ECDSA signature pair
     */
    function permit(
        address owner,
        address spender,
        uint256 amount,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(owner != address(0), "permit: signature");
        require(block.timestamp <= deadline, "permit: expired");

        bytes32 structHash = keccak256(abi.encode(PERMIT_TYPEHASH, owner, spender, amount, nonces[owner]++, deadline));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));

        address signatory = ecrecover(digest, v, r, s);
        require(signatory == owner, "permit: unauthorized");

        _approve(owner, spender, amount);
    }

    // @dev Pausing is optimized for speed of action. The guardian is intended to be the option with the least friction, though manager or affiliate can pause as well.
    function pause() external {
        require(msg.sender == guardian || msg.sender == manager || msg.sender == affiliate, "only-authorized-pausers");
        _pause();
    }

    // @dev Unpausing requires a higher permission level than pausing, which is optimized for speed of action. The manager or affiliate can unpause
    function unpause() external {
        require(msg.sender == manager || msg.sender == affiliate, "only-authorized-unpausers");
        _unpause();
    }

    // // @dev Withdrawal logic variant that processes withdrawal fees to affiliate
    // function _withdraw(
    //     address sender,
    //     address receiver,
    //     uint256 amount, // if `MAX_UINT256`, just withdraw everything
    //     bool withdrawFromBest // If true, also withdraw from `_bestVault`
    // ) internal override returns (uint256 withdrawn, uint256 fee, uint256 toReciever) {
    //     VaultAPI _bestVault = bestVault();

    //     VaultAPI[] memory vaults = allVaults();
    //     _updateVaultCache(vaults);

    //     for (uint256 id = 0; id < vaults.length; id++) {
    //         if (!withdrawFromBest && vaults[id] == _bestVault) {
    //             continue; // Don't withdraw from the best
    //         }

    //         // Start with the total shares that `sender` has
    //         uint256 availableShares = vaults[id].balanceOf(sender);

    //         // Restrict by the allowance that `sender` has to this contract
    //         // NOTE: No need for allowance check if `sender` is this contract
    //         if (sender != address(this)) {
    //             availableShares = MathUpgradeable.min(availableShares, vaults[id].allowance(sender, address(this)));
    //         }

    //         // Limit by maximum withdrawal size from each vault
    //         availableShares = MathUpgradeable.min(availableShares, vaults[id].maxAvailableShares());

    //         if (availableShares > 0) {
    //             // Intermediate step to move shares to this contract before withdrawing
    //             // NOTE: No need for share transfer if this contract is `sender`
    //             if (sender != address(this)) vaults[id].transferFrom(sender, address(this), availableShares);

    //             if (amount != WITHDRAW_EVERYTHING) {
    //                 // Compute amount to withdraw fully to satisfy the request
    //                 uint256 estimatedShares =
    //                     amount
    //                         .sub(withdrawn) // NOTE: Changes every iteration
    //                         .mul(10**uint256(vaults[id].decimals()))
    //                         .div(vaults[id].pricePerShare()); // NOTE: Every Vault is different

    //                 // Limit amount to withdraw to the maximum made available to this contract
    //                 uint256 shares = MathUpgradeable.min(estimatedShares, availableShares);
    //                 withdrawn = withdrawn.add(vaults[id].withdraw(shares));
    //             } else {
    //                 withdrawn = withdrawn.add(vaults[id].withdraw());
    //             }

    //             // Check if we have fully satisfied the request
    //             // NOTE: use `amount = WITHDRAW_EVERYTHING` for withdrawing everything
    //             if (amount <= withdrawn) break; // withdrawn as much as we needed
    //         }
    //     }

    //     // If we have extra, deposit back into `_bestVault` for `sender`
    //     // NOTE: Invariant is `withdrawn <= amount`
    //     if (withdrawn > amount) {
    //         // Don't forget to approve the deposit
    //         if (token.allowance(address(this), address(_bestVault)) < withdrawn.sub(amount)) {
    //             token.safeApprove(address(_bestVault), UNLIMITED_APPROVAL); // Vaults are trusted
    //         }

    //         _bestVault.deposit(withdrawn.sub(amount), sender);
    //         withdrawn = amount;
    //     }

    //     if (withdrawalFee > 0) {
    //         fee = withdrawn.mul(withdrawalFee).div(MAX_BPS);
    //         toReciever = withdrawn.sub(fee);
    //         token.safeTransfer(affiliate, fee);
    //     }

    //     // `receiver` now has `withdrawn` tokens as balance
    //     if (receiver != address(this)) token.safeTransfer(receiver, withdrawn);
    // }
}
