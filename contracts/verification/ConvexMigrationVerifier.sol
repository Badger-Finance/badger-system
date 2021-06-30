// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IBadgerGeyser.sol";

import "interfaces/sushi/ISushiChef.sol";
import "interfaces/uniswap/IUniswapPair.sol";
import "interfaces/sushi/IxSushi.sol";

import "interfaces/badger/IController.sol";
import "interfaces/badger/IMintr.sol";
import "interfaces/badger/IStrategy.sol";

import "interfaces/curve/ICurveGauge.sol";

import "interfaces/convex/IBooster.sol";
import "interfaces/convex/CrvDepositor.sol";
import "interfaces/convex/IClaimZap.sol";
import "interfaces/convex/IBaseRewardsPool.sol";

contract ConvexMigrationVerifier {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;
    
    // ===== Token Registry =====
    address public constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599; // WBTC Token
    address public constant weth = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // WETH token
    address public constant sushi = 0x6B3595068778DD592e39A122f4f5a5cF09C90fE2; // SUSHI token
    address public constant xsushi = 0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272; // xSUSHI token
    address public constant crv = 0xD533a949740bb3306d119CC777fa900bA034cd52; // CRV token
    address public constant cvx = 0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B; // CVX token
    address public constant cvxCrv = 0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7; // cvxCRV token

    IERC20Upgradeable public constant crvToken = IERC20Upgradeable(0xD533a949740bb3306d119CC777fa900bA034cd52); // CRV token
    IERC20Upgradeable public constant cvxToken = IERC20Upgradeable(0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B); // CVX token
    IERC20Upgradeable public constant cvxCrvToken = IERC20Upgradeable(0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7); // cvxCRV token
    IERC20Upgradeable public constant sushiToken = IERC20Upgradeable(0x6B3595068778DD592e39A122f4f5a5cF09C90fE2); // SUSHI token
    IERC20Upgradeable public constant xsushiToken = IERC20Upgradeable(0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272); // xSUSHI token

    // ===== Sushi Registry =====
    address public constant chef = 0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd; // Master staking contract

    // ===== Convex Registry =====
    CrvDepositor public constant crvDepositor = CrvDepositor(0x8014595F2AB54cD7c604B00E9fb932176fDc86Ae); // Convert CRV -> cvxCRV
    address public constant cvxCRV_CRV_SLP = 0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007; // cvxCRV/CRV SLP
    address public constant CVX_ETH_SLP = 0x05767d9EF41dC40689678fFca0608878fb3dE906; // CVX/ETH SLP
    IBooster public constant booster = IBooster(0xF403C135812408BFbE8713b5A23a04b3D48AAE31);
    ISushiChef public constant convexMasterChef = ISushiChef(0x5F465e9fcfFc217c5849906216581a657cd60605);
    IClaimZap public constant claimZap = IClaimZap(0xAb9F4BB0aDD2CFbb168da95C590205419cD71f9B);

    IERC20Upgradeable public constant cvxCRV_CRV_SLP_Token = IERC20Upgradeable(0x33F6DDAEa2a8a54062E021873bCaEE006CdF4007); // cvxCRV/CRV SLP
    IERC20Upgradeable public constant CVX_ETH_SLP_Token = IERC20Upgradeable(0x05767d9EF41dC40689678fFca0608878fb3dE906); // CVX/ETH SLP

    uint256 public constant cvxCRV_CRV_SLP_Pid = 0;
    uint256 public constant CVX_ETH_SLP_Pid = 1;

    uint256 public constant MAX_UINT_256 = uint256(-1);

    function runAndVerifyMigration(address want, address strategy, uint256 pid) external view returns (bool) {
        IBooster.PoolInfo memory poolInfo = booster.poolInfo(pid);
        IBaseRewardsPool baseRewardsPool = IBaseRewardsPool(poolInfo.crvRewards);

        // Pre-conditions

        // Run migration (be sure to run in context of strategist)

        // The gauge should have the appropriate increase in want
        // Convex baseRewardsPool should state the appropriate balance
    }
}
