import json
import time

from brownie import Wei, web3, chain
from dotmap import DotMap
from helpers.constants import AddressZero
from helpers.registry import registry
from helpers.time_utils import days, to_timestamp

with open("merkle/airdrop.json") as f:
    Airdrop = json.load(f)

curve = registry.curve
pickle = registry.pickle
harvest = registry.harvest
sushi = registry.sushi

pools = curve.pools

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
                withdrawalFee=75,
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
                withdrawalFee=75,
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
                withdrawalFee=75,
                keepCRV=0,
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
                withdrawalFee=75,
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
                withdrawalFee=75,
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
                withdrawalFee=50,
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

badger_config = DotMap(
    prod_json="deploy-final.json",
    test_mode=False,
    startMultiplier=1,
    endMultiplier=3,
    multisig=multisig_config,
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
        badgerLockAmount=badger_total_supply * 35 // 100, lockDuration=days(30),
    ),
    teamVestingParams=DotMap(
        startTime=globalStartTime, cliffDuration=days(30), totalDuration=days(365),
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
            badger=[DotMap(amount=Wei("45000 ether"), duration=days(7),)],  # 1 week
            uniBadgerWbtc=[
                DotMap(amount=Wei("65000 ether"), duration=days(7),)  # 1 week
            ],
            bSbtcCrv=[DotMap(amount=Wei("76750 ether"), duration=days(7),)],  # 1 week
            bRenCrv=[DotMap(amount=Wei("76750 ether"), duration=days(7),)],  # 1 week
            bTbtcCrv=[DotMap(amount=Wei("76750 ether"), duration=days(7),)],  # 1 week
            bSuperRenCrvPickle=[
                DotMap(amount=Wei("76750 ether"), duration=days(7),)  # 1 week
            ],
            bSuperRenCrvHarvest=[
                DotMap(amount=Wei("76750 ether"), duration=days(7),)  # 1 week
            ],
        ),
    ),
)


# TODO: Currently a copy of badger config params, needs to be set.
# diggStartTime = globalStartTime
diggStartTime = 1611097200 # 6PM EST 1/19

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
    airdropAmount = int(total_digg * airdrop_pct / 100),
    liquidityMiningAmount = int(total_digg * liquidity_mining_pct / 100),
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
        diggAmount=int(total_digg * dao_treasury_pct / 100),
        lockDuration=days(30)
    ),
    # TODO: Currently a copy of badger config params, needs to be set.
    teamVestingParams=DotMap(
        diggAmount=int(total_digg * team_vesting_pct / 100),
        startTime=diggStartTime,
        cliffDuration=days(30),
        totalDuration=days(365)
    ),
    geyserParams=DotMap(
        # TODO: Needs to be set
        diggDistributionStart=globalStartTime + days(15),
        unlockSchedules=DotMap(
            # Setting distribution amt to 25% for now.
            digg=[DotMap(amount=1000 * (10 ** digg_decimals), duration=days(7),)],  # 1 week
        ),
    ),
)

digg_config = DotMap(
    startTime=diggStartTime,
    prod_json="deploy-final.json",
    initialSupply=total_digg,
    airdropAmount = int(total_digg * airdrop_pct / 100),
    liquidityMiningAmount = int(total_digg * liquidity_mining_pct / 100),
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
        diggAmount=int(total_digg * dao_treasury_pct / 100),
        lockDuration=days(7)
    ),
    teamVestingParams=DotMap(
        diggAmount=int(total_digg * team_vesting_pct / 100),
        startTime=diggStartTime,
        cliffDuration=days(0),
        totalDuration=days(365)
    ),
    # TODO: Set this to the prod airdrop root
    airdropRoot="0xe083d1a60e1ca84c995048be8b9b5b4d4e371f31bcbdff8b775cb47502f4108b",
    airdropTotalShares="0x2666666666666600000000000000000000075fbb5707c39d0359f2ba7a800000",
    # TODO: Need to set this value to exact time we want allow reclaiming of airdrop.
    reclaimAllowedTimestamp=chain.time()
)

ren_config = DotMap(
    integrator="0x0",
    # Fees below are in bps.
    mintFeeBps=100,
    burnFeeBps=100,
    # 50/50 integrator/governance.
    percentageFeeIntegratorBps=5000,
    percentageFeeGovernanceBps=5000,
)

config = DotMap(
    badger=badger_config,
    sett=sett_config,
    digg=digg_config,
    ren=ren_config,
)
