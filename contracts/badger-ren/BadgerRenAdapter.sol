// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";

interface IGateway {
    function mint(
        bytes32 _pHash,
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external returns (uint256);

    function burn(bytes calldata _to, uint256 _amount) external returns (uint256);
}

interface IGatewayRegistry {
    function getGatewayBySymbol(string calldata _tokenSymbol) external view returns (IGateway);

    function getGatewayByToken(address _tokenAddress) external view returns (IGateway);

    function getTokenBySymbol(string calldata _tokenSymbol) external view returns (IERC20);
}

interface ICurveExchange {
    function exchange(
        int128 i,
        int128 j,
        uint256 dx,
        uint256 min_dy
    ) external;

    function get_dy(
        int128,
        int128 j,
        uint256 dx
    ) external view returns (uint256);

    function calc_token_amount(uint256[2] calldata amounts, bool deposit) external returns (uint256 amount);

    function add_liquidity(uint256[2] calldata amounts, uint256 min_mint_amount) external;

    function remove_liquidity(uint256 _amount, uint256[2] calldata min_amounts) external;

    function remove_liquidity_imbalance(uint256[2] calldata amounts, uint256 max_burn_amount) external;

    function remove_liquidity_one_coin(
        uint256 _token_amounts,
        int128 i,
        uint256 min_amount
    ) external;
}

//contract BadgerRenAdapter is Initializable {
contract BadgerRenAdapter {
    using SafeMathUpgradeable for uint256;
    using SafeERC20 for IERC20;

    IERC20 renBTC;
    IERC20 wBTC;

    // RenVM gateway registry.
    IGatewayRegistry public registry;
    // Curve exchange contract for the renBTC/wBTC pool.
    ICurveExchange public exchange;

    event RecoverStuckRenBTC(uint256 amount);
    event MintRenBTC(uint256 amount);
    event BurnRenBTC(uint256 amount);
    event MintWBTC(uint256 renbtc_minted, uint256 wbtc_bought);
    event BurnWBTC(uint256 wbtc_transferred, uint256 renbtc_burned);

    address public integrator;
    address public governance;

    uint256 public mintFeeBps;
    uint256 public burnFeeBps;
    uint256 private percentageFeeIntegratorBps;
    uint256 private percentageFeeGovernanceBps;

    uint256 public constant MAX_BPS = 10000;

    //function initialize(
    //    address _governance,
    //    address _integrator,
    //    address _registry,
    //    address _exchange,
    //    address _wbtc
    //) public {
    //    registry = IGatewayRegistry(_registry);
    //    exchange = ICurveExchange(_exchange);
    //    renBTC = registry.getTokenBySymbol("BTC");
    //    wBTC = IERC20(_wbtc);
    //}
    constructor(
        address _governance,
        address _integrator,
        address _registry,
        address _exchange,
        address _wbtc,
        uint256[4] memory _feeConfig,
    ) public {
        governance = _governance;
        integrator = _integrator;

        registry = IGatewayRegistry(_registry);
        exchange = ICurveExchange(_exchange);
        renBTC = registry.getTokenBySymbol("BTC");
        wBTC = IERC20(_wbtc);

        mintFeeBps = _feeConfig[0];
        burnFeeBps = _feeConfig[1];
        percentageFeeIntegratorBps = _feeConfig[2];
        percentageFeeGovernanceBps = _feeConfig[3];

        // Approve exchange.
        require(renBTC.approve(_exchange, uint256(-1)));
        require(wBTC.approve(_exchange, uint256(-1)));
    }

    function recoverStuck(
        bytes calldata encoded,
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external {
        // Ensure sender matches sender of original tx.
        uint256 start = encoded.length - 32;
        address sender = abi.decode(encoded[start:], (address));
        require(sender == msg.sender);

        bytes32 pHash = keccak256(encoded);
        uint256 mintedAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);

        emit RecoverStuckRenBTC(mintedAmount);

        renBTC.safeTransfer(msg.sender, mintedAmount);
    }

    function mintRenBTC(
        // user args
        address payable _renBTCDestination,
        // darknode args
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external {
        // Mint renBTC tokens
        bytes32 pHash = keccak256(abi.encode(_renBTCDestination));
        uint256 mintedAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);

        emit MintRenBTC(mintedAmount);

        renBTC.safeTransfer(_renBTCDestination, mintedAmount);
    }

    function burnRenBTC(bytes calldata _btcDestination, uint256 _amount) external {
        require(renBTC.balanceOf(address(msg.sender)) >= _amount);
        uint256 startRenbtcBalance = renBTC.balanceOf(address(this));
        renBTC.safeTransferFrom(msg.sender, address(this), _amount);
        uint256 endRenbtcBalance = renBTC.balanceOf(address(this));
        uint256 _transferred = endRenbtcBalance.sub(startRenbtcBalance);
        uint256 burnAmount = registry.getGatewayBySymbol("BTC").burn(_btcDestination, _transferred);

        emit BurnRenBTC(burnAmount);
    }

    event ExchangeWBTCBytesError(bytes error);
    event ExchangeWBTCStringError(string error);

    function mintWBTC(
        uint256 _slippage,
        address payable _wbtcDestination,
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external {
        // Mint renBTC tokens
        bytes32 pHash = keccak256(abi.encode(_slippage, _wbtcDestination));
        uint256 mintedAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);

        // Get price
        uint256 dy = exchange.get_dy(0, 1, mintedAmount);
        _slippage = uint256(1e4).sub(_slippage);
        uint256 min_dy = dy.mul(_slippage).div(1e4);

        uint256 startWbtcBalance = wBTC.balanceOf(address(this));
        try exchange.exchange(0, 1, mintedAmount, min_dy)  {
            uint256 endWbtcBalance = wBTC.balanceOf(address(this));
            uint256 wbtcBought = endWbtcBalance.sub(startWbtcBalance);
            emit MintWBTC(mintedAmount, wbtcBought);

            // Send converted wBTC to user.
            require(wBTC.transfer(_wbtcDestination, wbtcBought));
        } catch Error(string memory _error) {
            emit ExchangeWBTCStringError(_error);

            // Fallback to sending renBTC to user.
            emit MintRenBTC(mintedAmount);
            require(renBTC.transfer(_wbtcDestination, mintedAmount));
        } catch (bytes memory _error) {
            emit ExchangeWBTCBytesError(_error);

            // Fallback to sending renBTC to user.
            emit MintRenBTC(mintedAmount);
            require(renBTC.transfer(_wbtcDestination, mintedAmount));
        }
    }

    function burnWBTC(
        bytes calldata _btcDestination,
        uint256 _amount,
        uint256 _minRenbtcAmount
    ) external {
        wBTC.safeTransferFrom(msg.sender, address(this), _amount);
        uint256 startRenbtcBalance = renBTC.balanceOf(address(this));
        exchange.exchange(1, 0, _amount, _minRenbtcAmount);
        uint256 endRenbtcBalance = renBTC.balanceOf(address(this));
        uint256 renbtcBought = endRenbtcBalance.sub(startRenbtcBalance);

        // Burn and send proceeds to the User
        uint256 burnAmount = registry.getGatewayBySymbol("BTC").burn(_btcDestination, renbtcBought);
        emit BurnWBTC(_amount, burnAmount);
    }

    function _processFee(
        address token,
        uint256 amount,
        uint256 feeBps,
    ) internal returns (uint256) {
        if (feeBps == 0) {
            return 0;
        }
        uint256 fee = amount.mul(feeBps).div(MAX_BPS);
        uint256 governanceFee = fee.mul(percentageFeeGovernanceBps).div(MAX_BPS);
        uint256 integratorFee = fee.mul(percentageFeeIntegratorBps).div(MAX_BPS);
        IERC20(token).safeTransfer(governance, governanceFee);
        IERC20(token).safeTransfer(integrator, integratorFee);
        return fee;
    }
}
