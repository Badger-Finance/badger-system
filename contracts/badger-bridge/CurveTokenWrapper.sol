// SPDX-License-Identifier: MIT

pragma solidity ^0.6.8;

import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "deps/@openzeppelin/contracts/math/SafeMath.sol";

import "interfaces/bridge/IBridgeVault.sol";
import "interfaces/curve/ICurveFi.sol";

// Permissionless curve lp token wrapper contract.
// RenBTC must be transferred before calling wrap fns.
// Wrapped tokens will be transferred back to sender.
contract CurveTokenWrapper {
    /*
     * Currently only support curve lp pools that have renBTC as an asset.
     * We supply liquidity as renBTC to these pools.
     * Some lp pools require two deposits as they are a pool of other pool tokens (e.g. tbtc).
     *
     * Currently supported lp pools are:
     * - renbtc
     * - sbtc
     * - tbtc (requires depositng into sbtc lp pool first)
     *
     * We can consider implementing a generic curve token wrapper that accepts a wrap/unwrap path.
     */
    using SafeMath for uint256;
    using SafeERC20 for IERC20;

    // NB: Addresses are hardcoded to ETH addresses.
    // Supported tokens.
    IERC20 renbtc = IERC20(0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D);
    IERC20 renbtcLpToken = IERC20(0x49849C98ae39Fff122806C06791Fa73784FB3675);
    IERC20 sbtcLpToken = IERC20(0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3);
    IERC20 tbtcLpToken = IERC20(0x64eda51d3Ad40D56b9dFc5554E06F94e1Dd786Fd);

    // Supported pools.
    address renbtcPool = 0x93054188d876f558f4a66B2EF1d97d16eDf0895B;
    address sbtcPool = 0x7fC77b5c7614E1533320Ea6DDc2Eb61fa00A9714;
    address tbtcPool = 0xC25099792E9349C7DD09759744ea681C7de2cb66;

    constructor() public {}

    function wrap(address _vault) external returns (uint256) {
        uint256 amount = renbtc.balanceOf(address(this));
        if (amount == 0) {
            return 0;
        }

        IERC20 vaultToken = IBridgeVault(_vault).token();

        if (vaultToken == renbtcLpToken) {
            _approveBalance(renbtc, renbtcPool, amount);
            uint256[2] memory amounts = [amount, 0];
            ICurveFi(renbtcPool).add_liquidity(amounts, 0);
            uint256 toTransfer = renbtcLpToken.balanceOf(address(this));
            renbtcLpToken.safeTransfer(msg.sender, toTransfer);
            return toTransfer;
        }

        if (vaultToken == sbtcLpToken) {
            _approveBalance(renbtc, sbtcPool, amount);
            uint256[3] memory amounts = [amount, 0, 0];
            ICurveFi(sbtcPool).add_liquidity(amounts, 0);
            uint256 toTransfer = sbtcLpToken.balanceOf(address(this));
            sbtcLpToken.safeTransfer(msg.sender, toTransfer);
            return toTransfer;
        }

        // tbtcLpToken is doubly wrapped.
        if (vaultToken == tbtcLpToken) {
            _approveBalance(renbtc, sbtcPool, amount);
            uint256[3] memory amounts = [amount, 0, 0];
            ICurveFi(sbtcPool).add_liquidity(amounts, 0);

            uint256 sbtcAmount = sbtcLpToken.balanceOf(address(this));
            _approveBalance(sbtcLpToken, tbtcPool, sbtcAmount);
            uint256[2] memory tbtcPoolAmounts = [0, sbtcAmount];
            ICurveFi(tbtcPool).add_liquidity(tbtcPoolAmounts, 0);
            uint256 toTransfer = tbtcLpToken.balanceOf(address(this));
            tbtcLpToken.safeTransfer(msg.sender, toTransfer);
            return toTransfer;
        }
    }

    function unwrap(address _vault) external {
        IERC20 vaultToken = IBridgeVault(_vault).token();

        uint256 amount = vaultToken.balanceOf(address(this));
        if (amount == 0) {
            return;
        }

        if (vaultToken == renbtcLpToken) {
            ICurveFi(renbtcPool).remove_liquidity_one_coin(amount, 0, 0);
            uint256 toTransfer = renbtcLpToken.balanceOf(address(this));
            renbtcLpToken.safeTransfer(msg.sender, toTransfer);
            return;
        }

        if (vaultToken == sbtcLpToken) {
            ICurveFi(sbtcPool).remove_liquidity_one_coin(amount, 0, 0);
            uint256 toTransfer = sbtcLpToken.balanceOf(address(this));
            sbtcLpToken.safeTransfer(msg.sender, toTransfer);
            return;
        }

        // tbtcLpToken is doubly wrapped.
        if (vaultToken == tbtcLpToken) {
            ICurveFi(sbtcPool).remove_liquidity_one_coin(amount, 0, 0);

            amount = sbtcLpToken.balanceOf(address(this));
            ICurveFi(tbtcPool).remove_liquidity_one_coin(amount, 1, 0);
            uint256 toTransfer = tbtcLpToken.balanceOf(address(this));
            tbtcLpToken.safeTransfer(msg.sender, toTransfer);
            return;
        }
    }

    function _approveBalance(
        IERC20 _token,
        address _spender,
        uint256 _amount
    ) internal {
        if (_token.allowance(address(this), _spender) < _amount) {
            // Approve max spend.
            _token.safeApprove(_spender, (1 << 64) - 1);
        }
    }
}
