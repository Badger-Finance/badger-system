pragma solidity 0.6.6;

import {IRootERC721} from "../RootToken/IRootERC721.sol";
import {IERC721Receiver} from "deps/@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import {RLPReader} from "../../lib/RLPReader.sol";
import {ITokenPredicate} from "./ITokenPredicate.sol";
import {Initializable} from "../../common/Initializable.sol";
import {AccessControlMixin} from "../../common/AccessControlMixin.sol";

contract ERC721Predicate is ITokenPredicate, AccessControlMixin, Initializable, IERC721Receiver {
    using RLPReader for bytes;
    using RLPReader for RLPReader.RLPItem;

    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");
    bytes32 public constant TOKEN_TYPE = keccak256("ERC721");
    // keccak256("Transfer(address,address,uint256)")
    bytes32 public constant TRANSFER_EVENT_SIG = 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef;
    // keccak256("WithdrawnBatch(address,uint256[])")
    bytes32 public constant WITHDRAW_BATCH_EVENT_SIG = 0xf871896b17e9cb7a64941c62c188a4f5c621b86800e3d15452ece01ce56073df;
    // keccak256("TransferWithMetadata(address,address,uint256,bytes)")
    bytes32 public constant TRANSFER_WITH_METADATA_EVENT_SIG = 0xf94915c6d1fd521cee85359239227480c7e8776d7caf1fc3bacad5c269b66a14;

    // limit batching of tokens due to gas limit restrictions
    uint256 public constant BATCH_LIMIT = 20;

    event LockedERC721(address indexed depositor, address indexed depositReceiver, address indexed rootToken, uint256 tokenId);
    event LockedERC721Batch(address indexed depositor, address indexed depositReceiver, address indexed rootToken, uint256[] tokenIds);

    constructor() public {}

    function initialize(address _owner) external initializer {
        _setupContractId("ERC721Predicate");
        _setupRole(DEFAULT_ADMIN_ROLE, _owner);
        _setupRole(MANAGER_ROLE, _owner);
    }

    /**
     * @notice accepts safe ERC721 transfer
     */
    function onERC721Received(
        address,
        address,
        uint256,
        bytes calldata
    ) external override returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }

    /**
     * @notice Lock ERC721 tokens for deposit, callable only by manager
     * @param depositor Address who wants to deposit token
     * @param depositReceiver Address (address) who wants to receive token on child chain
     * @param rootToken Token which gets deposited
     * @param depositData ABI encoded tokenId
     */
    function lockTokens(
        address depositor,
        address depositReceiver,
        address rootToken,
        bytes calldata depositData
    ) external override only(MANAGER_ROLE) {
        // deposit single
        if (depositData.length == 32) {
            uint256 tokenId = abi.decode(depositData, (uint256));
            emit LockedERC721(depositor, depositReceiver, rootToken, tokenId);
            IRootERC721(rootToken).safeTransferFrom(depositor, address(this), tokenId);

            // deposit batch
        } else {
            uint256[] memory tokenIds = abi.decode(depositData, (uint256[]));
            emit LockedERC721Batch(depositor, depositReceiver, rootToken, tokenIds);
            uint256 length = tokenIds.length;
            require(length <= BATCH_LIMIT, "ERC721Predicate: EXCEEDS_BATCH_LIMIT");
            for (uint256 i; i < length; i++) {
                IRootERC721(rootToken).safeTransferFrom(depositor, address(this), tokenIds[i]);
            }
        }
    }

    /**
     * @notice Validates log signature, from and to address
     * then sends the correct tokenId to withdrawer
     * callable only by manager
     * @param rootToken Token which gets withdrawn
     * @param log Valid ERC721 burn log from child chain
     */
    function exitTokens(
        address,
        address rootToken,
        bytes memory log
    ) public override only(MANAGER_ROLE) {
        RLPReader.RLPItem[] memory logRLPList = log.toRlpItem().toList();
        RLPReader.RLPItem[] memory logTopicRLPList = logRLPList[1].toList(); // topics
        address withdrawer = address(logTopicRLPList[1].toUint()); // topic1 is from address

        if (bytes32(logTopicRLPList[0].toUint()) == TRANSFER_EVENT_SIG) {
            // topic0 is event sig
            require(
                address(logTopicRLPList[2].toUint()) == address(0), // topic2 is to address
                "ERC721Predicate: INVALID_RECEIVER"
            );

            IRootERC721(rootToken).safeTransferFrom(
                address(this),
                withdrawer,
                logTopicRLPList[3].toUint() // topic3 is tokenId field
            );
        } else if (bytes32(logTopicRLPList[0].toUint()) == WITHDRAW_BATCH_EVENT_SIG) {
            // topic0 is event sig
            bytes memory logData = logRLPList[2].toBytes();
            uint256[] memory tokenIds = abi.decode(logData, (uint256[])); // data is tokenId list
            uint256 length = tokenIds.length;
            for (uint256 i; i < length; i++) {
                IRootERC721(rootToken).safeTransferFrom(address(this), withdrawer, tokenIds[i]);
            }
        } else if (bytes32(logTopicRLPList[0].toUint()) == TRANSFER_WITH_METADATA_EVENT_SIG) {
            // If this is when NFT exit is done with arbitrary metadata on L2

            require(
                address(logTopicRLPList[2].toUint()) == address(0), // topic2 is to address
                "ERC721Predicate: INVALID_RECEIVER"
            );

            IRootERC721 token = IRootERC721(rootToken);
            uint256 tokenId = logTopicRLPList[3].toUint(); // topic3 is tokenId field

            token.safeTransferFrom(address(this), withdrawer, tokenId);
            // This function will be invoked for passing arbitrary
            // metadata, obtained from event emitted in L2, to
            // L1 ERC721, so that it can decode & do further processing
            //
            // @note Make sure you've implemented this method
            // if you're interested in exiting with metadata
            bytes memory logData = logRLPList[2].toBytes();
            bytes memory metaData = abi.decode(logData, (bytes));

            token.setTokenMetadata(tokenId, metaData);
        } else {
            revert("ERC721Predicate: INVALID_SIGNATURE");
        }
    }
}
