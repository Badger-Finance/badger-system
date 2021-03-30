// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "./BaseWrapperUpgradeable.sol";

import "interfaces/yearn/VaultAPI.sol";
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

    /// @notice A record of states for signing / validating signatures
    mapping(address => uint256) public nonces;

    address public affiliate;

    address public pendingAffiliate;

    // ===== GatedUpgradeable additional parameters =====

    GuestListAPI public guestList;

    address public manager;

    address public guardian;

    modifier onlyAffiliate() {
        require(msg.sender == affiliate);
        _;
    }

    event PendingAffiliate(address affiliate);
    event AcceptAffiliate(address affiliate);
    event SetGuardian(address guardian);
    event SetManager(address manager);
    event UpdateGuestList(address guestList);

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

        emit SetGuardian(guardian);
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
        return 10**uint256(decimals());
    }

    function _sharesForValue(uint256 amount) internal view returns (uint256) {
        uint256 totalWrapperAssets = totalVaultBalance(address(this));

        if (totalWrapperAssets > 0) {
            return totalSupply().mul(amount).div(totalWrapperAssets);
        } else {
            return amount;
        }
    }

    function deposit() external returns (uint256) {
        return deposit(uint256(-1)); // Deposit everything
    }

    function deposit(uint256 amount) public returns (uint256 deposited) {
        if (address(guestList) != address(0)) {
            require(guestList.authorized(msg.sender, amount), "guest-list-authorization");
        }
        
        uint256 shares = _sharesForValue(amount); // NOTE: Must be calculated before deposit is handled
        deposited = _deposit(msg.sender, address(this), amount, true); // `true` = pull from `msg.sender`
        _mint(msg.sender, shares);
    }

    function withdraw() external returns (uint256) {
        return withdraw(balanceOf(msg.sender));
    }

    function withdraw(uint256 shares) public returns (uint256) {
        _burn(msg.sender, shares);
        return _withdraw(address(this), msg.sender, _shareValue(shares), true); // `true` = withdraw from `bestVault`
    }

    function migrate() external onlyAffiliate returns (uint256) {
        return _migrate(address(this));
    }

    function migrate(uint256 amount) external onlyAffiliate returns (uint256) {
        return _migrate(address(this), amount);
    }

    function migrate(uint256 amount, uint256 maxMigrationLoss) external onlyAffiliate returns (uint256) {
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

}
