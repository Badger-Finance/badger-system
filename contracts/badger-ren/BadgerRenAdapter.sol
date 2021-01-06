// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
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

    function getTokenBySymbol(string calldata _tokenSymbol) external view returns (IERC20Upgradeable);
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

contract BadgerRenAdapter is Initializable {
    using SafeMathUpgradeable for uint256;
    using SafeERC20Upgradeable for IERC20Upgradeable;

    IERC20Upgradeable renBTC;
    IERC20Upgradeable wBTC;

    // RenVM gateway registry.
    IGatewayRegistry public registry;
    // Curve exchange contract for the renBTC/wBTC pool.
    ICurveExchange public exchange;

    event RecoverStuckRenBTC(uint256 amount);
    event MintRenBTC(uint256 amount);
    event BurnRenBTC(uint256 amount);
    event MintWBTC(uint256 renbtc_minted, uint256 wbtc_bought);
    event BurnWBTC(uint256 wbtc_transferred, uint256 renbtc_burned);

    function initialize(
        address _registry,
        address _exchange,
        address _wbtc
    ) public {
        registry = IGatewayRegistry(_registry);
        exchange = ICurveExchange(_exchange);
        renBTC = registry.getTokenBySymbol("BTC");
        wBTC = IERC20Upgradeable(_wbtc);
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
        require(renBTC.balanceOf(address(this)) >= _amount);
        uint256 burnAmount = registry.getGatewayBySymbol("BTC").burn(_btcDestination, _amount);

        emit BurnRenBTC(burnAmount);
    }

    function mintWBTC(
        uint256 _minExchangeRate,
        uint256 _newMinExchangeRate,
        uint256 _slippage,
        address payable _wbtcDestination,
        uint256 _amount,
        bytes32 _nHash,
        bytes calldata _sig
    ) external {
        // Mint renBTC tokens
        bytes32 pHash = keccak256(abi.encode(_minExchangeRate, _slippage, _wbtcDestination, msg.sender));
        uint256 mintedAmount = registry.getGatewayBySymbol("BTC").mint(pHash, _amount, _nHash, _sig);

        // Get price
        uint256 dy = exchange.get_dy(0, 1, mintedAmount);
        uint256 rate = dy.mul(1e8).div(mintedAmount);
        _slippage = uint256(1e4).sub(_slippage);
        uint256 min_dy = dy.mul(_slippage).div(1e4);

        // Price is OK
        if (rate >= _newMinExchangeRate) {
            uint256 startWbtcBalance = wBTC.balanceOf(address(this));
            exchange.exchange(0, 1, mintedAmount, min_dy);

            uint256 endWbtcBalance = wBTC.balanceOf(address(this));
            uint256 wbtcBought = endWbtcBalance.sub(startWbtcBalance);

            //Send proceeds to the User
            require(wBTC.transfer(_wbtcDestination, wbtcBought));
            emit MintWBTC(mintedAmount, wbtcBought);
        } else {
            //Send renBTC to the User instead
            require(renBTC.transfer(_wbtcDestination, mintedAmount));
            emit MintRenBTC(mintedAmount);
        }
    }

    function burnWBTC(
        bytes calldata _btcDestination,
        uint256 _amount,
        uint256 _minRenbtcAmount
    ) external {
        require(wBTC.transferFrom(msg.sender, address(this), _amount));
        uint256 startRenbtcBalance = renBTC.balanceOf(address(this));
        exchange.exchange(1, 0, _amount, _minRenbtcAmount);
        uint256 endRenbtcBalance = renBTC.balanceOf(address(this));
        uint256 renbtcBought = endRenbtcBalance.sub(startRenbtcBalance);

        // Burn and send proceeds to the User
        uint256 burnAmount = registry.getGatewayBySymbol("BTC").burn(_btcDestination, renbtcBought);
        emit BurnWBTC(_amount, burnAmount);
    }
}
