import json
import time

from brownie import Wei, web3
from dotmap import DotMap
from helpers.constants import AddressZero
from helpers.registry import registry
from helpers.time_utils import days, days, hours

with open("merkle/airdrop.json") as f:
    Airdrop = json.load(f)

curve = registry.curve
pickle = registry.pickle
harvest = registry.harvest

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
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=75,
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
        initialSharesPerToken=10 ** 6,
        founderRewardPercentage=10,
        badgerDistributionStart=globalStartTime,
        diggDistributionStart=globalStartTime + days(15),
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

# trial_badger_config = badger_config
# trial_badger_config.globalStartTime = 1606957257
# trial_badger_config.tokenLockParams.lockDuration = hours(1.5)  # Unlock to DAO
# trial_badger_config.teamVestingParams.cliffDuration = hours(
#     1.5
# )  # Unlock to founders, cliff
# trial_badger_config.teamVestingParams.totalDuration = hours(6)
# trial_badger_config.geyserParams.badgerDistributionStart = 1606951800


"""
    tokenLockParams=DotMap(
        badgerLockAmount=badger_total_supply * 35 // 100,
        lockDuration=days(30),
    ),
    teamVestingParams=DotMap(
        startTime=globalStartTime,
        cliffDuration=days(30),
        totalDuration=days(365),
    ),
"""

digg_config = DotMap(
    initialSupply=6250 * (10 ** 9),
    deviationThreshold=50000000000000000,
    rebaseLag=10,
    minRebaseTimeIntervalSec=86400,
    rebaseWindowOffsetSec=7200,
    rebaseWindowLengthSec=1200,
    baseCpi=10 ** 18,
    rebaseDelayAfterStakingStart=30,
    marketOracleParams=DotMap(
        reportExpirationTimeSec=88200, reportDelaySec=3600, minimumProviders=1,
    ),
    cpiOracleParams=DotMap(
        reportExpirationTimeSec=5356800, reportDelaySec=86400, minimumProviders=1,
    ),
    centralizedOracleParams=DotMap(
        owners=[AddressZero, AddressZero, AddressZero], threshold=1,
    ),
    tokenLockParams=DotMap(diggLockAmount=3125 * (10 ** 9), lockDuration=days(30),),
)

config = DotMap(badger=badger_config, sett=sett_config, digg=digg_config)
