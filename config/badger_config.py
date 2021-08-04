import json
import time

from brownie import Wei, web3, chain
from dotmap import DotMap
from helpers.proxy_utils import deploy_proxy
from helpers.constants import AddressZero
from helpers.registry import registries
from helpers.time_utils import days, to_timestamp

with open("merkle/airdrop.json") as f:
    Airdrop = json.load(f)

registry = registries.get_registry("eth")
curve = registry.curve
pickle = registry.pickle
harvest = registry.harvest
sushi = registry.sushi
pools = curve.pools
chainlink = registry.chainlink
convex = registry.convex

sett_config = DotMap(
    native=DotMap(
        badger=DotMap(
            strategyName="StrategyBadgerRewards",
            params=DotMap(
                # want = Badger token
                # geyser = Special Geyser
                performanceFeeStrategist=0,
                performanceFeeGovernance=0,
                withdrawalFee=0,
            ),
        ),
        uniBadgerWbtc=DotMap(
            strategyName="StrategyBadgerLpMetaFarm",
            params=DotMap(
                # Note: Will not be able to be deployed until the LP token is created
                # want = Uni Badger<>Wbtc LP
                performanceFeeStrategist=0,
                performanceFeeGovernance=0,
                withdrawalFee=0,
            ),
        ),
        sbtcCrv=DotMap(
            strategyName="StrategyCurveGauge",
            params=DotMap(
                want=pools.sbtcCrv.token,
                gauge=pools.sbtcCrv.gauge,
                swap=pools.sbtcCrv.swap,
                minter=curve.minter,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=20,
                keepCRV=0,
            ),
        ),
        renCrv=DotMap(
            strategyName="StrategyCurveGauge",
            params=DotMap(
                want=pools.renCrv.token,
                gauge=pools.renCrv.gauge,
                swap=pools.renCrv.swap,
                minter=curve.minter,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=20,
                keepCRV=0,
            ),
        ),
        tbtcCrv=DotMap(
            strategyName="StrategyCurveGauge",
            params=DotMap(
                want=pools.tbtcCrv.token,
                gauge=pools.tbtcCrv.gauge,
                swap=pools.tbtcCrv.swap,
                minter=curve.minter,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=20,
                keepCRV=0,
            ),
        ),
        convexRenCrv=DotMap(
            strategyName="StrategyConvexStakingOptimizer",
            params=DotMap(
                want=pools.renCrv.token,
                pid=curve.pids.renCrv,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=0,
                performanceFeeGovernance=2000,
                withdrawalFee=20,
                curvePool=DotMap(
                    swap=registry.curve.pools.renCrv.swap,
                    wbtcPosition=1,
                    numElements=2,
                ),
                cvxHelperVault=convex.cvxHelperVault,
                cvxCrvHelperVault=convex.cvxCrvHelperVault,
            ),
        ),
        convexSbtcCrv=DotMap(
            strategyName="StrategyConvexStakingOptimizer",
            params=DotMap(
                want=pools.sbtcCrv.token,
                pid=curve.pids.sbtcCrv,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=0,
                performanceFeeGovernance=2000,
                withdrawalFee=20,
                curvePool=DotMap(
                    swap=registry.curve.pools.sbtcCrv.swap,
                    wbtcPosition=1,
                    numElements=3,
                ),
                cvxHelperVault=convex.cvxHelperVault,
                cvxCrvHelperVault=convex.cvxCrvHelperVault,
            ),
        ),
        convexTbtcCrv=DotMap(
            strategyName="StrategyConvexStakingOptimizer",
            params=DotMap(
                want=pools.tbtcCrv.token,
                pid=curve.pids.tbtcCrv,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=0,
                performanceFeeGovernance=2000,
                withdrawalFee=20,
                curvePool=DotMap(
                    swap=registry.curve.pools.tbtcCrv.swap,
                    wbtcPosition=2,
                    numElements=4,
                ),
                cvxHelperVault=convex.cvxHelperVault,
                cvxCrvHelperVault=convex.cvxCrvHelperVault,
            ),
        ),
        convexHbtcCrv=DotMap(
            strategyName="StrategyConvexStakingOptimizer",
            params=DotMap(
                want=pools.hbtcCrv.token,
                pid=curve.pids.hbtcCrv,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=0,
                performanceFeeGovernance=2000,
                withdrawalFee=20,
                curvePool=DotMap(
                    swap=registry.curve.pools.hbtcCrv.swap,
                    wbtcPosition=1,
                    numElements=2,
                ),
                cvxHelperVault=convex.cvxHelperVault,
                cvxCrvHelperVault=convex.cvxCrvHelperVault,
            ),
        ),
        convexObtcCrv=DotMap(
            strategyName="StrategyConvexStakingOptimizer",
            params=DotMap(
                want=pools.obtcCrv.token,
                pid=curve.pids.obtcCrv,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=0,
                performanceFeeGovernance=2000,
                withdrawalFee=20,
                curvePool=DotMap(
                    swap=registry.curve.pools.obtcCrv.swap,
                    wbtcPosition=2,
                    numElements=4,
                ),
                cvxHelperVault=convex.cvxHelperVault,
                cvxCrvHelperVault=convex.cvxCrvHelperVault,
            ),
        ),
        convexPbtcCrv=DotMap(
            strategyName="StrategyConvexStakingOptimizer",
            params=DotMap(
                want=pools.pbtcCrv.token,
                pid=curve.pids.pbtcCrv,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=0,
                performanceFeeGovernance=2000,
                withdrawalFee=20,
                curvePool=DotMap(
                    swap=registry.curve.pools.pbtcCrv.swap,
                    wbtcPosition=2,
                    numElements=4,
                ),
                cvxHelperVault=convex.cvxHelperVault,
                cvxCrvHelperVault=convex.cvxCrvHelperVault,
            ),
        ),
        convexBbtcCrv=DotMap(
            strategyName="StrategyConvexStakingOptimizer",
            params=DotMap(
                want=pools.bbtcCrv.token,
                pid=curve.pids.bbtcCrv,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=0,
                performanceFeeGovernance=2000,
                withdrawalFee=20,
                curvePool=DotMap(
                    swap=registry.curve.pools.bbtcCrv.swap,
                    wbtcPosition=2,
                    numElements=4,
                ),
                cvxHelperVault=convex.cvxHelperVault,
                cvxCrvHelperVault=convex.cvxCrvHelperVault,
            ),
        ),
        convexTriCrypto=DotMap(
            strategyName="StrategyConvexStakingOptimizer",
            params=DotMap(
                want=pools.triCrypto.token,
                pid=curve.pids.triCrypto,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=0,
                performanceFeeGovernance=2000,
                withdrawalFee=20,
                curvePool=DotMap(
                    swap=registry.curve.pools.triCrypto.swap,
                    wbtcPosition=1,
                    numElements=3,
                ),
                cvxHelperVault=convex.cvxHelperVault,
                cvxCrvHelperVault=convex.cvxCrvHelperVault,
            ),
        ),
        convexTriCryptoDos=DotMap(
            strategyName="StrategyConvexStakingOptimizer",
            params=DotMap(
                want=pools.triCryptoDos.token,
                pid=curve.pids.triCryptoDos,
                lpComponent=registry.tokens.wbtc,
                performanceFeeStrategist=0,
                performanceFeeGovernance=2000,
                withdrawalFee=20,
                curvePool=DotMap(
                    swap=registry.curve.pools.triCryptoDos.swap,
                    wbtcPosition=1,
                    numElements=3,
                ),
                cvxHelperVault=convex.cvxHelperVault,
                cvxCrvHelperVault=convex.cvxCrvHelperVault,
            ),
        ),
    ),
    helper=DotMap(
        cvx=DotMap(
            strategyName="StrategyCvxHelper",
            params=DotMap(
                want=registry.tokens.cvx,
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=20,
            ),
        ),
        cvxCrv=DotMap(
            strategyName="StrategyCvxCrvHelper",
            params=DotMap(
                want=registry.tokens.cvxCrv,
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=20,
            ),
        ),
    ),
    pickle=DotMap(
        renCrv=DotMap(
            strategyName="StrategyPickleMetaFarm",
            params=DotMap(
                want=pools.renCrv.token,
                pickleJar=pickle.jars.renCrv,
                curveSwap=registry.curve.pool.renCrv.swap,
                lpComponent=registry.tokens.wbtc,
                pid=pickle.pids.pRenCrv,
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=20,
            ),
        ),
    ),
    harvest=DotMap(
        renCrv=DotMap(
            # Unfinished
            strategyName="StrategyHarvestMetaFarm",
            params=DotMap(
                want=pools.renCrv.token,
                harvestVault=registry.harvest.vaults.renCrv,
                vaultFarm=registry.harvest.farms.fRenCrv,
                metaFarm=registry.harvest.farms.farm,
                badgerTree=registry.harvest.badgerTree,
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=20,
            ),
        ),
    ),
    uni=DotMap(
        uniDiggWbtc=DotMap(
            # Unfinished
            strategyName="StrategyDiggLpMetaFarm",
            params=DotMap(
                performanceFeeStrategist=0,
                performanceFeeGovernance=0,
                withdrawalFee=0,
            ),
        ),
        uniGenericLp=DotMap(
            strategyName="StrategyUniGenericLp",
            params=DotMap(
                withdrawalFee=0,
            ),
        ),
    ),
    sushi=DotMap(
        sushiBadgerWBtc=DotMap(
            # Unfinished
            strategyName="StrategySushiBadgerWbtc",
            params=DotMap(
                # want=pools.renCrv.token,
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=0,
            ),
        ),
        sushiWethWBtc=DotMap(
            # Unfinished
            strategyName="StrategySushiBadgerWbtc",
            params=DotMap(
                # want=pools.renCrv.token,
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=20,
            ),
        ),
        sushiDiggWBtc=DotMap(
            # Unfinished
            strategyName="StrategySushiDiggWbtcLpOptimizer",
            params=DotMap(
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=0,
            ),
        ),
        # These params generically cover all CLAW strategies.
        sushiClawUSDC=DotMap(
            strategyName="StrategySushiLpOptimizer",
            params=DotMap(
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=0,
            ),
        ),
        sushiWbtcIbBtc=DotMap(
            params=DotMap(
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=0,
            ),
        ),
    ),
    pancake=DotMap(
        pancakeBnbBtcb=DotMap(
            strategyName="StrategyPancakeLpOptimizer",
            params=DotMap(
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=20,
            ),
        ),
    ),
)

badger_total_supply = Wei("21000000 ether")

multisig_config = DotMap(
    address="0xB65cef03b9B89f99517643226d76e286ee999e77",
    owners=[
        "0xe24b6bF43d4624B2E146D3F871e19b7ECb811208",
        "0x211b82242076792A07C7554A5B968F0DE4414938",
        "0xe7bab002A39f9672a1bD0E949d3128eeBd883575",
        "0x59c68A651a1f49C26145666E9D5647B1472912A9",
        "0x15b8Fe651C268cfb5b519cC7E98bd45C162313C2",
    ],
)

dao_config = DotMap(
    initialOwner=web3.toChecksumAddress("0xDA25ee226E534d868f0Dd8a459536b03fEE9079b"),
    token="0x3472a5a71965499acd81997a54bba8d852c6e53d",
    kernel="0x33D53383314190B0B885D1b6913B5a50E2D3A639",
    agent="0x8de82c4c968663a0284b01069dde6ef231d0ef9b",
)

globalStartTime = 1607014800

geyser_keys = [
    "native.uniBadgerWbtc",
    "harvest.renCrv",
    "native.sbtcCrv",
    "native.tbtcCrv",
    "native.renCrv",
    "native.badger",
    "native.sushiBadgerWbtc",
    "native.sushiWbtcEth",
    "native.uniDiggWbtc",
    "native.sushiDiggWbtc",
]

badger_config = DotMap(
    prod_json="deploy-final.json",
    test_mode=False,
    startMultiplier=1,
    endMultiplier=3,
    multisig=multisig_config,
    opsMultisig=DotMap(address="0x576cD258835C529B54722F84Bb7d4170aA932C64"),
    dao=dao_config,
    globalStartTime=globalStartTime,
    huntParams=DotMap(
        startTime=int(time.time()),
        badgerAmount=badger_total_supply * 10 // 100,
        gracePeriod=days(2),
        epochDuration=days(1),
        merkleRoot=Airdrop["merkleRoot"],
        claimReductionPerEpoch=2000,
    ),
    founderRewardsAmount=badger_total_supply * 10 // 100,
    initialHuntAmount=badger_total_supply * 5 // 100,
    rewardsEscrowBadgerAmount=badger_total_supply * 40 // 100,
    tokenLockParams=DotMap(
        badgerLockAmount=badger_total_supply * 35 // 100,
        lockDuration=days(30),
    ),
    teamVestingParams=DotMap(
        startTime=globalStartTime,
        cliffDuration=days(30),
        totalDuration=days(365),
    ),
    devMultisigParams=DotMap(
        threshold=1,
        to=AddressZero,
        data="0x",
        fallbackHandler=AddressZero,
        paymentToken=AddressZero,
        payment=0,
        paymentReceiver=AddressZero,
    ),
    daoParams=DotMap(
        tokenName="Badger",
        tokenSymbol="BADGER",
        id="badger-finance",
        initialSupply=badger_total_supply,
        financePeriod=0,
        useAgentAsVault=True,
        supportRequired=Wei("0.5 ether"),
        minAcceptanceQuorum=Wei("0.05 ether"),
        voteDuration=days(3),
    ),
    geyserParams=DotMap(
        badgerDistributionStart=globalStartTime,
        unlockSchedules=DotMap(
            badger=[
                DotMap(
                    amount=Wei("45000 ether"),
                    duration=days(7),
                )
            ],  # 1 week
            uniBadgerWbtc=[
                DotMap(
                    amount=Wei("65000 ether"),
                    duration=days(7),
                )  # 1 week
            ],
            bSbtcCrv=[
                DotMap(
                    amount=Wei("76750 ether"),
                    duration=days(7),
                )
            ],  # 1 week
            bRenCrv=[
                DotMap(
                    amount=Wei("76750 ether"),
                    duration=days(7),
                )
            ],  # 1 week
            bTbtcCrv=[
                DotMap(
                    amount=Wei("76750 ether"),
                    duration=days(7),
                )
            ],  # 1 week
            bSuperRenCrvPickle=[
                DotMap(
                    amount=Wei("76750 ether"),
                    duration=days(7),
                )  # 1 week
            ],
            bSuperRenCrvHarvest=[
                DotMap(
                    amount=Wei("76750 ether"),
                    duration=days(7),
                )  # 1 week
            ],
        ),
    ),
)


# TODO: Currently a copy of badger config params, needs to be set.
# diggStartTime = globalStartTime
diggStartTime = 1611097200  # 6PM EST 1/19

"""
Test Config
- Rebases can be called at anytime
- Anyone can call the oracle to set the price
- Assets are distributed among
"""
digg_decimals = 9
total_digg = 4000 * (10 ** digg_decimals)

liquidity_mining_pct = 40
dao_treasury_pct = 40
team_vesting_pct = 5
airdrop_pct = 15

digg_config_test = DotMap(
    startTime=diggStartTime,
    prod_json="deploy-final.json",
    initialSupply=total_digg,
    airdropAmount=int(total_digg * airdrop_pct / 100),
    liquidityMiningAmount=int(total_digg * liquidity_mining_pct / 100),
    deviationThreshold=50000000000000000,
    rebaseLag=10,
    # TODO: Need to set this value to exact time we want to start rebases.
    minRebaseTimeIntervalSec=86400,  # 24 hours (once per day)
    rebaseWindowOffsetSec=72000,  # 8pm UTC
    rebaseWindowLengthSec=1200,  # 20 minute window
    baseCpi=10 ** 18,
    marketOracleParams=DotMap(
        # NB: Longer report expiration for testing purposes.
        # We want this to cover two full rebase windows to account
        # for shifting the rebase window forward during tests.
        reportExpirationTimeSec=86400 * 2,
        reportDelaySec=3600,
        # TODO: This should be greater than 1, needs to be set.
        minimumProviders=1,
    ),
    # cpi oracle always reports 1
    cpiOracleParams=DotMap(
        # TODO: The median oracle caps report expiration time
        # at 520 weeks.There is no way to guarantee report non-expiry.
        # Maybe look into a constant oracle that adheres to the IOracle interface.
        reportExpirationTimeSec=520 * 7 * 24 * 60 * 60,  # 520 weeks
        reportDelaySec=7200,
        minimumProviders=1,
    ),
    centralizedOracleParams=DotMap(
        owners=[AddressZero, AddressZero, AddressZero],
        threshold=1,
    ),
    tokenLockParams=DotMap(
        diggAmount=int(total_digg * dao_treasury_pct / 100), lockDuration=days(30)
    ),
    # TODO: Currently a copy of badger config params, needs to be set.
    teamVestingParams=DotMap(
        diggAmount=int(total_digg * team_vesting_pct / 100),
        startTime=diggStartTime,
        cliffDuration=days(30),
        totalDuration=days(365),
    ),
    geyserParams=DotMap(
        # TODO: Needs to be set
        diggDistributionStart=globalStartTime + days(15),
        unlockSchedules=DotMap(
            # Setting distribution amt to 25% for now.
            digg=[
                DotMap(
                    amount=1000 * (10 ** digg_decimals),
                    duration=days(7),
                )
            ],  # 1 week
        ),
    ),
)

digg_config = DotMap(
    startTime=diggStartTime,
    prod_json="deploy-final.json",
    initialSupply=total_digg,
    airdropAmount=int(total_digg * airdrop_pct / 100),
    liquidityMiningAmount=int(total_digg * liquidity_mining_pct / 100),
    deviationThreshold=50000000000000000,
    rebaseLag=10,
    # TODO: Need to set this value to exact time we want to start rebases.
    minRebaseTimeIntervalSec=86400,  # 24 hours (once per day)
    rebaseWindowOffsetSec=72000,  # 8pm UTC
    rebaseWindowLengthSec=1200,  # 20 minute window
    baseCpi=10 ** 18,
    marketOracleParams=DotMap(
        reportExpirationTimeSec=88200,
        reportDelaySec=3600,
        # TODO: This should be greater than 1, needs to be set.
        minimumProviders=1,
    ),
    # cpi oracle always reports 1
    cpiOracleParams=DotMap(
        reportExpirationTimeSec=5356800,
        reportDelaySec=86400,
        minimumProviders=1,
    ),
    centralizedOracleParams=DotMap(
        owners=[AddressZero, AddressZero, AddressZero],
        threshold=1,
    ),
    tokenLockParams=DotMap(
        diggAmount=int(total_digg * dao_treasury_pct / 100), lockDuration=days(7)
    ),
    teamVestingParams=DotMap(
        diggAmount=int(total_digg * team_vesting_pct / 100),
        startTime=diggStartTime,
        cliffDuration=days(0),
        totalDuration=days(365),
    ),
    # TODO: Set this to the prod airdrop root
    airdropRoot="0xe083d1a60e1ca84c995048be8b9b5b4d4e371f31bcbdff8b775cb47502f4108b",
    airdropTotalShares="0x2666666666666600000000000000000000075fbb5707c39d0359f2ba7a800000",
    # TODO: Need to set this value to exact time we want allow reclaiming of airdrop.
    reclaimAllowedTimestamp=chain.time(),
)

"""
NB: The CLAW system config primarily specifies default values for the
parameterization of EMP (expiring multiparty synthetic contracts).

Also note that in the future we may be migrating to perpetual
multiparty synthetics (to be released by UMA team).

All Addresses below are MAINNET addresses.

Most numerical values are denominated in wei.
"""
claw_config = DotMap(
    # NB: This is just for writing out deployment addrs during local testing.
    prod_json="deploy-claw.json",
    empCreatorAddress="0xB3De1e212B49e68f4a68b5993f31f63946FCA2a6",
    # This represents the delta in days to be applied to now.
    # Actual param is `expirationTimestamp`.
    # NB: It is recommended by UMA to set expiry @ 10:00 pm UTC on expiry date.
    expirationTimestampDaysDelta=days(60),  # Rolling w/ 2 month lifespan EMPs.
    collateralRequirement=1.2
    * 10 ** 18,  # Default UMA specified min collateral requirement is 1.2.
    disputeBondPercentage=0.1 * 10 ** 18,
    sponsorDisputeRewardPercentage=0.1 * 10 ** 18,
    disputerDisputeRewardPercentage=0.1 * 10 ** 18,
    # This represents the minimum dollar value required to mint synthetics.
    # The default value below of $100 in wei is a balance between sponsors setting a position
    # so small that there's no incentive to liquidate and setting a value too large so that
    # smaller sponsors get priced out (also creates problems for small liquidators).
    minSponsorTokens=100 * 10 ** 18,
    withdrawalLiveness=7200,  # Default UMA specified min is at least 2 hours.
    liquidationLiveness=7200,  # Default UMA specified min is at least 2 hours.
    # Should be set to the UMA contract store, address below is the MAINNET address.
    excessTokenBeneficiary="0x54f44eA3D2e7aA0ac089c4d8F7C93C27844057BF",
    # Technically these are expiring but we will NEVER have more than a single active
    # at any point in time.
    emps=DotMap(
        sClaw=DotMap(
            symbol="sCLAW",
            priceFeedIdentifier="0x5553442d5b62774254432f45544820534c505d00000000000000000000000000",
            collateralAddress="0x758A43EE2BFf8230eeb784879CdcFF4828F2544D",
        ),
        bClaw=DotMap(
            symbol="bCLAW",
            priceFeedIdentifier="0x5553442f62426164676572000000000000000000000000000000000000000000",
            collateralAddress="0x19D97D8fA813EE2f51aD4B4e04EA08bAf4DFfC28",
        ),
    ),
)

bridge_config = DotMap(
    # Mainnet addr for the renVM gateway registry
    # See: https://docs.renproject.io/developers/docs/deployed-contracts
    registry="0xe80d347DF1209a76DD9d2319d62912ba98C54DDD",
    # Dev multisig
    governance=multisig_config.address,
    rewards="0xE95b56685327C9caf83C3e6F0A54b8D9708f32c4",
    wbtc=registry.tokens.wbtc,
    # Fees below are in bps.
    mintFeeBps=25,
    burnFeeBps=40,
    # 50/50 rewards/governance.
    percentageFeeRewardsBps=5000,
    percentageFeeGovernanceBps=5000,
)

swap_config = DotMap(
    adminMultiSig=multisig_config.address,  # dev multisig
    strategies=DotMap(
        curve=DotMap(
            # Mainnet addr for the curve registry address provider.
            # See: https://curve.readthedocs.io/registry-address-provider.html
            registry="0x0000000022D53366457F9d5E68Ec105046FC4383",
        ),
    ),
)

config = DotMap(
    badger=badger_config,
    sett=sett_config,
    digg=digg_config,
    claw=claw_config,
    bridge=bridge_config,
    swap=swap_config,
)
