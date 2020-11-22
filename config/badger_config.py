from brownie import Wei
from helpers.time_utils import daysToSeconds
from helpers.constants import AddressZero
import time
from helpers.registry import registry
from dotmap import DotMap

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
    address="0x28Ae60E4EFdFb4F0b0CC501b2DEDCa6acF3eA629",
    owners=["0x66aB6D9362d4F35596279692F0251Db635165871"]
)

dao_config = DotMap(
    initialOwner="0xcD9e6Df80169b6a2CFfDaE613fAbC3F7C3647B14",
    token="0xa24d4966a753a72411cc11228e3a066f44ece326",
    kernel="0x3E3ABAe73F459dA1747D3cf891798eee54CD5ed7",
    agent="0x292f498041423035d6ed66fc4873dc466f5959b8"
)

badger_config = DotMap(
    multisig=multisig_config,
    dao=dao_config,
    globalStartTime=int((time.time())),
    huntParams=DotMap(
        startTime=int(time.time()), badgerAmount=badger_total_supply * 15 // 100, gracePeriod=daysToSeconds(2), epochDuration=daysToSeconds(1)
    ),
    rewardsEscrowBadgerAmount=badger_total_supply * 50 // 100,
    tokenLockParams=DotMap(
        badgerLockAmount=badger_total_supply * 35 // 100,
        lockDuration=daysToSeconds(30),
    ),
    teamVestingParams=DotMap(
        startTime=(int(time.time())),
        cliffDuration=daysToSeconds(1),
        totalDuration=daysToSeconds(364),
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
        voteDuration=daysToSeconds(7),
    ),
    geyserParams=DotMap(
        initialSharesPerToken=10 ** 6,
        founderRewardPercentage=10,
        badgerDistributionStart=int((time.time())),
        diggDistributionStart=int((time.time()) + daysToSeconds(15)),
        unlockSchedules=DotMap(
            badger=[
                DotMap(
                    amount=Wei("90000 ether"),
                    duration=daysToSeconds(7),  # 1 week
                )
            ],
            uniBadgerWbtc=[
                DotMap(
                    amount=Wei("130000 ether"),
                    duration=daysToSeconds(7),  # 1 week
                )
            ],
            bSbtcCrv=[
                DotMap(
                    amount=Wei("76750 ether"),
                    duration=daysToSeconds(7),  # 1 week
                )
            ],
            bRenCrv=[
                DotMap(
                    amount=Wei("76750 ether"),
                    duration=daysToSeconds(7),  # 1 week
                )
            ],
            bTbtcCrv=[
                DotMap(
                    amount=Wei("76750 ether"),
                    duration=daysToSeconds(7),  # 1 week
                )
            ],
            bSuperRenCrvPickle=[
                DotMap(
                    amount=Wei("76750 ether"),
                    duration=daysToSeconds(7),  # 1 week
                )
            ],
            bSuperRenCrvHarvest=[
                DotMap(
                    amount=Wei("76750 ether"),
                    duration=daysToSeconds(7),  # 1 week
                )
            ],
        ),
    ),
)

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
    tokenLockParams=DotMap(
        diggLockAmount=3125 * (10 ** 9), lockDuration=daysToSeconds(30),
    ),
)

config = DotMap(badger=badger_config, sett=sett_config, digg=digg_config)
