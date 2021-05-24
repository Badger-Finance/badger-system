pragma solidity 0.6.6;

import {ERC20} from "deps/maticnetwork/pos-portal@1.5.2/contracts/child/ChildToken/UpgradeableChildERC20/ERC20.sol";
import {IChildToken} from "deps/maticnetwork/pos-portal@1.5.2/contracts/child/ChildToken/IChildToken.sol";
import {AccessControlMixin} from "deps/maticnetwork/pos-portal@1.5.2/contracts/common/AccessControlMixin.sol";
import {NativeMetaTransaction} from "deps/maticnetwork/pos-portal@1.5.2/contracts/common/NativeMetaTransaction.sol";
import {ContextMixin} from "deps/maticnetwork/pos-portal@1.5.2/contracts/common/ContextMixin.sol";

contract UpgradeableChildProxyERC20 is ERC20, IChildToken, AccessControlMixin, NativeMetaTransaction, ContextMixin {
    bytes32 public constant DEPOSITOR_ROLE = keccak256("DEPOSITOR_ROLE");

    constructor() public ERC20("", "") {}

    /**
     * @notice Initialize the contract after it has been proxified
     * @dev meant to be called once immediately after deployment
     */
    function initialize(
        string calldata name_,
        string calldata symbol_,
        uint8 decimals_,
        address childChainManager
    ) external initializer {
        setName(name_);
        setSymbol(symbol_);
        setDecimals(decimals_);
        _setupContractId(string(abi.encodePacked("Child", symbol_)));
        _setupRole(DEFAULT_ADMIN_ROLE, _msgSender());
        _setupRole(DEPOSITOR_ROLE, childChainManager);
        _initializeEIP712(name_);
    }

    // This is to support Native meta transactions
    // never use msg.sender directly, use _msgSender() instead
    function _msgSender() internal override view returns (address payable sender) {
        return ContextMixin.msgSender();
    }

    function changeName(string calldata name_) external only(DEFAULT_ADMIN_ROLE) {
        setName(name_);
        _setDomainSeperator(name_);
    }

    /**
     * @notice called when token is deposited on root chain
     * @dev Should be callable only by ChildChainManager
     * Should handle deposit by minting the required amount for user
     * Make sure minting is done only by this function
     * @param user user address for whom deposit is being done
     * @param depositData abi encoded amount
     */
    function deposit(address user, bytes calldata depositData) external override only(DEPOSITOR_ROLE) {
        uint256 amount = abi.decode(depositData, (uint256));
        _mint(user, amount);
    }

    /**
     * @notice called when user wants to withdraw tokens back to root chain
     * @dev Should burn user's tokens. This transaction will be verified when exiting on root chain
     * @param amount amount of tokens to withdraw
     */
    function withdraw(uint256 amount) external {
        _burn(_msgSender(), amount);
    }
}
