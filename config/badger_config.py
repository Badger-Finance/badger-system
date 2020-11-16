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
                # rewardsSett = badger native Sett
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
                lpComponent=registry.tokens.tbtc,
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
                performanceFeeStrategist=1000,
                performanceFeeGovernance=1000,
                withdrawalFee=75,
            ),
        ),
    ),
)

badger_config = DotMap(
    huntParams=DotMap(startTime=int(time.time())),
    tokenLockParams=DotMap(
        badgerLockAmount=Wei("10500000 ether"),
        lockDuration=daysToSeconds(30),
        releaseTime=int((time.time()) + daysToSeconds(30)),
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
        initialSupply=Wei("21000000 ether"),
        financePeriod=0,
        useAgentAsVault=True,
        supportRequired=Wei("0.5 ether"),
        minAcceptanceQuorum=Wei("0.05 ether"),
        voteDuration=daysToSeconds(7),
    ),
    geyserParams=DotMap(
        initialSharesPerToken=10 ** 6,
        founderRewardPercentage=10,
        badgerDistributionStart=int((time.time()) + daysToSeconds(1)),
        diggDistributionStart=int((time.time()) + daysToSeconds(15)),
        unlockSchedules=DotMap(
            badger=[
                DotMap(
                    amount=Wei("2000000 ether"),
                    duration=daysToSeconds(8 * 7),  # 8 weeks
                    rewardMultiplier=1,
                )
            ],
            badgerWbtcUni=[
                DotMap(
                    amount=Wei("2000000 ether"),
                    duration=daysToSeconds(8 * 7),  # 8 weeks
                    rewardMultiplier=1,
                )
            ],
            bSbtcCrv=[
                DotMap(
                    amount=Wei("2000000 ether"),
                    rewardMultiplier=1,
                    duration=daysToSeconds(8 * 7),  # 8 weeks
                )
            ],
            bRenCrv=[
                DotMap(
                    amount=Wei("2000000 ether"),
                    duration=daysToSeconds(8 * 7),  # 8 weeks
                    rewardMultiplier=1,
                )
            ],
            bTbtcCrv=[
                DotMap(
                    amount=Wei("2000000 ether"),
                    duration=daysToSeconds(8 * 7),  # 8 weeks
                    rewardMultiplier=1,
                )
            ],
            bSuperSbtcCrv=[
                DotMap(
                    amount=Wei("2000000 ether"),
                    duration=daysToSeconds(8 * 7),  # 8 weeks
                    rewardMultiplier=1.2,
                )
            ],
            bSuperRenCrv=[
                DotMap(
                    amount=Wei("2000000 ether"),
                    duration=daysToSeconds(8 * 7),  # 8 weeks
                    rewardMultiplier=1.2,
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

