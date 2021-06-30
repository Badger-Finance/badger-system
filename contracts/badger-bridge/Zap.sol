pragma solidity 0.6.11;

import {IERC20} from "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20, SafeMath} from "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

//import "deps/@openzeppelin/contracts/token/ERC20/IERC20.sol";
//import "deps/@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

//import {AccessControlDefended} from "./AccessControlDefended.sol";

import {ISett} from "interfaces/badger/ISett.sol";
import {IBadgerYearnWbtcPeak} from "interfaces/bridge/IBadgerYearnWbtcPeak.sol";
import {IBadgerSettPeak} from "interfaces/bridge/IBadgerSettPeak.sol";
import {IbBTC} from "interfaces/defidollar/IbBTC.sol";
import {IbyvWbtc} from "interfaces/defidollar/IbyvWbtc.sol";

contract Zap {
    using SafeERC20 for IERC20;
    using SafeMath for uint;

    IBadgerSettPeak public constant settPeak = IBadgerSettPeak(0x41671BA1abcbA387b9b2B752c205e22e916BE6e3);
    IBadgerYearnWbtcPeak public constant byvWbtcPeak = IBadgerYearnWbtcPeak(0x825218beD8BE0B30be39475755AceE0250C50627);
    IbBTC public constant ibbtc = IbBTC(0xc4E15973E6fF2A35cC804c2CF9D2a1b817a8b40F);

    IERC20 public constant ren = IERC20(0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D);
    IERC20 public constant wbtc = IERC20(0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599);

    struct Pool {
        IERC20 lpToken;
        ICurveFi deposit;
        ISett sett;
    }
    Pool[4] public pools;

    constructor() public {
        pools[0] = Pool({ // crvRenWBTC [ ren, wbtc ]
            lpToken: IERC20(0x49849C98ae39Fff122806C06791Fa73784FB3675),
            deposit: ICurveFi(0x93054188d876f558f4a66B2EF1d97d16eDf0895B),
            sett: ISett(0x6dEf55d2e18486B9dDfaA075bc4e4EE0B28c1545)
        });
        pools[1] = Pool({ // crvRenWSBTC [ ren, wbtc, sbtc ]
            lpToken: IERC20(0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3),
            deposit: ICurveFi(0x7fC77b5c7614E1533320Ea6DDc2Eb61fa00A9714),
            sett: ISett(0xd04c48A53c111300aD41190D63681ed3dAd998eC)
        });
        pools[2] = Pool({ // tbtc-sbtcCrv [ tbtc, ren, wbtc, sbtc ]
            lpToken: IERC20(0x64eda51d3Ad40D56b9dFc5554E06F94e1Dd786Fd),
            deposit: ICurveFi(0xaa82ca713D94bBA7A89CEAB55314F9EfFEdDc78c),
            sett: ISett(0xb9D076fDe463dbc9f915E5392F807315Bf940334)
        });
        pools[3] = Pool({ // Exclusive to wBTC
            lpToken: wbtc,
            deposit: ICurveFi(0x0),
            sett: ISett(0x4b92d19c11435614CD49Af1b589001b7c08cD4D5) // byvWbtc
        });

        // Since we don't hold any tokens in this contract, we can optimize gas usage in mint calls by providing infinite approvals
        for (uint i = 0; i < pools.length; i++) {
            Pool memory pool = pools[i];
            pool.lpToken.safeApprove(address(pool.sett), uint(-1));
            if (i < 3) {
                ren.safeApprove(address(pool.deposit), uint(-1));
                wbtc.safeApprove(address(pool.deposit), uint(-1));
                IERC20(address(pool.sett)).safeApprove(address(settPeak), uint(-1));
            } else {
                IERC20(address(pool.sett)).safeApprove(address(byvWbtcPeak), uint(-1));
            }
        }
    }

    /**
    * @notice Mint ibbtc with wBTC / renBTC
    * @param token wBTC or renBTC address
    * @param amount wBTC or renBTC amount
    * @param poolId 0=crvRenWBTC, 1=crvRenWSBTC, 2=tbtc-sbtcCrv, 3=yvWbtc
    * @param idx Index of the token in the curve pool while adding liquidity; redundant for yvWbtc
    * @param minOut Minimum amount of ibbtc to mint. Use for capping slippage while adding liquidity to curve pool.
    * @return _ibbtc Minted ibbtc amount
    */
    function mint(IERC20 token, uint amount, uint poolId, uint idx, uint minOut)
        external
        returns(uint _ibbtc)
    {
        Pool memory pool = pools[poolId];

        token.safeTransferFrom(msg.sender, address(this), amount);

        if (poolId < 3) { // setts
            _addLiquidity(pool.deposit, amount, poolId + 2, idx); // pools are such that the #tokens they support is +2 from their poolId.
            pool.sett.deposit(pool.lpToken.balanceOf(address(this)));
            _ibbtc = settPeak.mint(poolId, pool.sett.balanceOf(address(this)), new bytes32[](0));
        } else if (poolId == 3) { // byvwbtc
            IbyvWbtc(address(pool.sett)).deposit(new bytes32[](0)); // pulls all available
            _ibbtc = byvWbtcPeak.mint(pool.sett.balanceOf(address(this)), new bytes32[](0));
        } else {
            revert("INVALID_POOL_ID");
        }

        require(_ibbtc >= minOut, "INSUFFICIENT_IBBTC"); // used for capping slippage in curve pools
        IERC20(address(ibbtc)).safeTransfer(msg.sender, _ibbtc);
    }

    /**
    * @dev Add liquidity to curve btc pools
    * @param amount wBTC / renBTC amount
    * @param pool Curve btc pool
    * @param numTokens # supported tokens for the curve pool
    * @param idx Index of the supported token in the curve pool in question
    */
    function _addLiquidity(ICurveFi pool, uint amount, uint numTokens, uint idx) internal {
        if (numTokens == 2) {
            uint[2] memory amounts;
            amounts[idx] = amount;
            pool.add_liquidity(amounts, 0);
        }

        if (numTokens == 3) {
            uint[3] memory amounts;
            amounts[idx] = amount;
            pool.add_liquidity(amounts, 0);
        }

        if (numTokens == 4) {
            uint[4] memory amounts;
            amounts[idx] = amount;
            pool.add_liquidity(amounts, 0);
        }
    }

    /**
    * @notice Calculate the most optimal route and expected ibbtc amount when minting with wBTC / renBtc.
    * @dev Use returned params poolId, idx and bBTC in the call to mint(...)
           The last param `minOut` in mint(...) should be a bit more than the returned bBTC value.
           For instance 0.2% - 1% higher depending on slippage tolerange.
    * @param amount renBTC amount
    * @return poolId 0=crvRenWBTC, 1=crvRenWSBTC, 2=tbtc-sbtcCrv, 3=byvwbtc
    * @return idx Index of the supported token in the curve pool (poolId). Should be ignored for poolId=3
    * @return bBTC Expected ibbtc. Not for precise calculations. Doesn't factor in (deposit) fee charged by the curve pool / byvwbtc.
    * @return fee Fee being charged by ibbtc system. Denominated in corresponding sett token
    */
    function calcMint(address token, uint amount) external view returns(uint poolId, uint idx, uint bBTC, uint fee) {
        if (token == address(ren)) {
            return calcMintWithRen(amount);
        }
        if (token == address(wbtc)) {
            return calcMintWithWbtc(amount);
        }
        revert("INVALID_TOKEN");
    }

    /**
    * @notice Calculate the most optimal route and expected ibbtc amount when minting with renBTC.
    * @dev Use returned params poolId, idx and bBTC in the call to mint(...)
           The last param `minOut` in mint(...) should be a bit more than the returned bBTC value.
           For instance 0.2% - 1% higher depending on slippage tolerange.
    * @param amount renBTC amount
    * @return poolId 0=crvRenWBTC, 1=crvRenWSBTC, 2=tbtc-sbtcCrv
    * @return idx Index of the supported token in the curve pool (poolId)
    * @return bBTC Expected ibbtc. Not for precise calculations. Doesn't factor in fee charged by the curve pool
    * @return fee Fee being charged by ibbtc system. Denominated in corresponding sett token
    */
    function calcMintWithRen(uint amount) public view returns(uint poolId, uint idx, uint bBTC, uint fee) {
        uint _ibbtc;
        uint _fee;

        // poolId=0, idx=0
        (bBTC, fee) = curveLPToIbbtc(0, pools[0].deposit.calc_token_amount([amount,0], true));

        (_ibbtc, _fee) = curveLPToIbbtc(1, pools[1].deposit.calc_token_amount([amount,0,0], true));
        if (_ibbtc > bBTC) {
            bBTC = _ibbtc;
            fee = _fee;
            poolId = 1;
            // idx=0
        }
        (_ibbtc, _fee) = curveLPToIbbtc(2, pools[2].deposit.calc_token_amount([0,amount,0,0], true));
        if (_ibbtc > bBTC) {
            bBTC = _ibbtc;
            fee = _fee;
            poolId = 2;
            idx = 1;
        }
    }

    /**
    * @notice Calculate the most optimal route and expected ibbtc amount when minting with wBTC.
    * @dev Use returned params poolId, idx and bBTC in the call to mint(...)
           The last param `minOut` in mint(...) should be a bit more than the returned bBTC value.
           For instance 0.2% - 1% higher depending on slippage tolerange.
    * @param amount renBTC amount
    * @return poolId 0=crvRenWBTC, 1=crvRenWSBTC, 2=tbtc-sbtcCrv, 3=byvwbtc
    * @return idx Index of the supported token in the curve pool (poolId). Should be ignored for poolId=3
    * @return bBTC Expected ibbtc. Not for precise calculations. Doesn't factor in (deposit) fee charged by the curve pool / byvwbtc.
    * @return fee Fee being charged by ibbtc system. Denominated in corresponding sett token
    */
    function calcMintWithWbtc(uint amount) public view returns(uint poolId, uint idx, uint bBTC, uint fee) {
        uint _ibbtc;
        uint _fee;

        // poolId=0
        (bBTC, fee) = curveLPToIbbtc(0, pools[0].deposit.calc_token_amount([0,amount], true));
        idx = 1;


        (_ibbtc, _fee) = curveLPToIbbtc(1, pools[1].deposit.calc_token_amount([0,amount,0], true));
        if (_ibbtc > bBTC) {
            bBTC = _ibbtc;
            fee = _fee;
            poolId = 1;
            // idx=1
        }

        (_ibbtc, _fee) = curveLPToIbbtc(2, pools[2].deposit.calc_token_amount([0,0,amount,0], true));
        if (_ibbtc > bBTC) {
            bBTC = _ibbtc;
            fee = _fee;
            poolId = 2;
            idx = 2;
        }

        // for byvwbtc, sett.pricePerShare returns a wbtc value, as opposed to lpToken amount in setts
        (_ibbtc, _fee) = byvWbtcPeak.calcMint(amount.mul(1e8).div(IbyvWbtc(address(pools[3].sett)).pricePerShare()));
        if (_ibbtc > bBTC) {
            bBTC = _ibbtc;
            fee = _fee;
            poolId = 3;
            // idx value will be ignored anyway
        }
    }

    /**
    * @dev Curve LP token amount to expected ibbtc amount
    */
    function curveLPToIbbtc(uint poolId, uint _lp) public view returns(uint bBTC, uint fee) {
        Pool memory pool = pools[poolId];
        uint _sett = _lp.mul(1e18).div(pool.sett.getPricePerFullShare());
        (bBTC, fee) = settPeak.calcMint(poolId, _sett);
    }

    function ibbtcToCurveLP(uint poolId, uint _ibbtc) public view returns(uint lp) {
        uint sett; 
        uint fee; 
        uint max;
        Pool memory pool = pools[poolId];
        (sett, fee, max) = settPeak.calcRedeem(poolId, _ibbtc);
        lp = sett.mul(pool.sett.getPricePerFullShare()).div(1e18); //reverse calculation
        return lp;
    }

    function calcRedeem(address token, uint amount) external view returns(uint poolId) {
        if (token == address(ren)) {
            return calcRedeemWithRenbtc(amount);
        }
        if (token == address(wbtc)) {
            return calcRedeemWithWbtc(amount);
        }
        revert("INVALID_TOKEN");
    }

    function calcRedeemWithRenbtc(uint amount) public view returns(uint poolId) {
        uint _renbtcMax;
        uint _renbtc;

        _renbtcMax = pools[0].deposit.calc_withdraw_one_coin(ibbtcToCurveLP(0, amount), 0);

        _renbtc = pools[1].deposit.calc_withdraw_one_coin(ibbtcToCurveLP(1, amount), 0);
        if (_renbtc > _renbtcMax) {
            _renbtcMax = _renbtc;
            poolId = 1;
        }

        _renbtc = pools[2].deposit.calc_withdraw_one_coin(ibbtcToCurveLP(2, amount), 1);
        if (_renbtc > _renbtcMax) {
            _renbtcMax = _renbtc;
            poolId = 2;
        }
    }

    function calcRedeemWithWbtc(uint amount) public view returns(uint poolId) {
        uint _wbtcMax;
        uint _wbtc;
        uint _byvwbtc;
        uint max;
        uint fee;

        // poolId=0
        _wbtcMax = pools[0].deposit.calc_withdraw_one_coin(ibbtcToCurveLP(0, amount), 1);

        _wbtc = pools[1].deposit.calc_withdraw_one_coin(ibbtcToCurveLP(1, amount), 1);
        if (_wbtc > _wbtcMax) {
            _wbtcMax = _wbtc;
            poolId = 1;
        }

        _wbtc = pools[2].deposit.calc_withdraw_one_coin(ibbtcToCurveLP(2, amount), 2);
        if (_wbtc > _wbtcMax) {
            _wbtcMax = _wbtc;
            poolId = 2;
        }

        (_byvwbtc, fee, max) = byvWbtcPeak.calcRedeem(amount); //the calcredeem returns byvwbtc sett tokens
        _wbtc = _byvwbtc.mul(IbyvWbtc(address(pools[3].sett)).pricePerShare()).div(1e8); //reverse arpit's calculation in the calcmint for sett->wbtc 
        if (_wbtc > _wbtcMax) {
            _wbtcMax = _wbtc;
            poolId = 3;
        }
    }
}

interface ICurveFi {
    function add_liquidity(uint[2] calldata amounts, uint min_mint_amount) external;
    function calc_token_amount(uint[2] calldata amounts, bool isDeposit) external view returns(uint);

    function add_liquidity(uint[3] calldata amounts, uint min_mint_amount) external;
    function calc_token_amount(uint[3] calldata amounts, bool isDeposit) external view returns(uint);

    function add_liquidity(uint[4] calldata amounts, uint min_mint_amount) external;
    function calc_token_amount(uint[4] calldata amounts, bool isDeposit) external view returns(uint);

    function calc_withdraw_one_coin(uint256 _token_amount, int128 i) external view returns(uint256);
}

interface IyvWbtc {
    function deposit(uint) external;
}