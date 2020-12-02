from helpers.time_utils import daysToSeconds
from brownie import *
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from config.badger_config import badger_config
from scripts.systems.badger_system import BadgerSystem
from rich.console import Console
import pytest
import brownie

console = Console()

"""
Ensure everything is configured as expected immediately post-deploy
"""


def confirm_controller_params(controller, params):
    assert controller.governance() == params.governance
    assert controller.strategist() == params.strategist
    assert controller.keeper() == params.keeper

    assert controller.rewards() == params.rewards

    for sett in params.setts:
        print(sett)
        assert controller.vaults(sett[0]) == sett[1]
        assert controller.strategies(sett[0]) == sett[2]


def confirm_sett_params(sett, params):
    assert sett.governance() == params.governance
    assert sett.strategist() == params.strategist
    assert sett.keeper() == params.keeper

    console.log(sett.name(), sett.symbol())

    assert sett.controller() == params.controller
    assert sett.token() == params.token
    assert sett.name() == params.name
    assert sett.symbol() == params.symbol

    assert sett.totalSupply() == 0
    assert sett.min() == params.min


def confirm_strategy_common_params(strategy, params):
    assert strategy.governance() == params.governance
    # assert strategy.strategist() == params.strategist
    assert strategy.keeper() == params.keeper

    assert strategy.controller() == params.controller
    assert strategy.guardian() == params.guardian

    assert strategy.getName() == params.name
    assert strategy.want() == params.want
    assert strategy.MAX_FEE() == 10000
    assert strategy.uniswap() == registry.uniswap.routerV2

    assert strategy.performanceFeeGovernance() == params.performanceFeeGovernance
    assert strategy.performanceFeeStrategist() == params.performanceFeeStrategist
    assert strategy.withdrawalFee() == params.withdrawalFee


def confirm_strategy_harvest_meta_farm_params(strategy, params):
    assert strategy.harvestVault() == params.harvestVault
    assert strategy.vaultFarm() == params.vaultFarm
    assert strategy.metaFarm() == params.metaFarm
    assert strategy.badgerTree() == params.badgerTree

    assert strategy.farm() == registry.harvest.farmToken
    assert strategy.depositHelper() == registry.harvest.depositHelper
    assert strategy.weth() == registry.tokens.weth

    assert (
        strategy.farmPerformanceFeeGovernance() == params.farmPerformanceFeeGovernance
    )
    assert (
        strategy.farmPerformanceFeeStrategist() == params.farmPerformanceFeeStrategist
    )


def confirm_strategy_pickle_meta_farm_params(strategy, params):
    assert strategy.pickleJar() == params.pickleJar
    assert strategy.pid() == params.pid
    assert strategy.curveSwap() == params.curveSwap
    assert strategy.lpComponent() == params.lpComponent

    assert strategy.pickle() == registry.pickle.pickleToken
    assert strategy.pickleChef() == registry.pickle.pickleChef
    assert strategy.pickleStaking() == registry.pickle.pickleStaking
    assert strategy.weth() == registry.tokens.weth
    assert strategy.wbtc() == registry.tokens.wbtc

    assert (
        strategy.picklePerformanceFeeGovernance()
        == params.picklePerformanceFeeGovernance
    )
    assert (
        strategy.picklePerformanceFeeStrategist()
        == params.picklePerformanceFeeStrategist
    )
    assert strategy.lastHarvested() == 0


def confirm_strategy_badger_rewards_params(strategy, params):
    assert strategy.geyser() == params.geyser


def confirm_strategy_badger_lp_meta_farm_params(strategy, params):
    assert strategy.geyser() == params.geyser


def confirm_rewards_escrow_params(rewardsEscrow, params):
    assert rewardsEscrow.owner() == params.owner


def confirm_badger_hunt_params(badgerHunt, params):
    assert badgerHunt.MAX_BPS() == 10000
    assert badgerHunt.claimsStart() == params.claimsStart
    assert badgerHunt.gracePeriod() == params.gracePeriod
    assert badgerHunt.epochDuration() == params.epochDuration
    assert badgerHunt.rewardReductionPerEpoch() == params.rewardReductionPerEpoch
    assert badgerHunt.currentRewardRate() == params.currentRewardRate
    assert badgerHunt.rewardsEscrow() == params.rewardsEscrow


def confirm_staking_rewards_params(rewards, params):
    assert rewards.hasRole(APPROVED_STAKER_ROLE, params.approvedStaker) == True
    assert rewards.getRoleMemberCount(APPROVED_STAKER_ROLE) == 1


def confirm_simple_timelock_params(timelock, params):
    assert timelock.token() == params.token
    assert timelock.beneficiary() == params.beneficiary
    assert timelock.releaseTime() == params.releaseTime


def confirm_smart_vesting_params(vesting, params):
    assert vesting.token() == params.token
    assert vesting.beneficiary() == params.beneficiary
    assert vesting.governor() == params.governor
    assert vesting.start() == params.start
    assert vesting.duration() == params.duration


def confirm_badger_geyser_params(geyser, params):
    for tokenLocker in params.tokenLockers:
        assert geyser.hasRole(TOKEN_LOCKER_ROLE, tokenLocker) == True

    assert geyser.getRoleMemberCount(TOKEN_LOCKER_ROLE) == len(params.tokenLockers)

    assert geyser.hasRole(DEFAULT_ADMIN_ROLE, params.admin) == True
    assert geyser.getRoleMemberCount(DEFAULT_ADMIN_ROLE) == 1

    assert geyser.MAX_PERCENTAGE() == 100
    assert (
        geyser.globalStartTime() == badger_config.geyserParams.badgerDistributionStart
    )
    assert geyser.supportsHistory() == False
    assert geyser.getStakingToken() == params.stakingToken
    assert geyser.totalStaked() == 0
    assert geyser.getNumDistributionTokens() == 1
    assert geyser.getDistributionTokens()[0] == params.initialDistributionToken


def confirm_badger_tree_params(badger, tree, params):
    assert tree.DEFAULT_ADMIN_ROLE() == DEFAULT_ADMIN_ROLE
    assert tree.getRoleMemberCount(DEFAULT_ADMIN_ROLE) == 1
    print(tree.getRoleMember(DEFAULT_ADMIN_ROLE, 0))
    assert tree.hasRole(DEFAULT_ADMIN_ROLE, params.admin) == True

    assert tree.hasRole(ROOT_UPDATER_ROLE, params.rootUpdater) == True
    assert tree.getRoleMemberCount(ROOT_UPDATER_ROLE) == 1

    assert tree.hasRole(GUARDIAN_ROLE, params.guardian) == True
    assert tree.getRoleMemberCount(GUARDIAN_ROLE) == 1

    assert tree.currentCycle() == 0
    assert tree.merkleRoot() == EmptyBytes32
    assert tree.merkleContentHash() == EmptyBytes32
    assert badger.token.balanceOf(tree) == params.initialBalance


def test_confirm_setup_sett(badger_prod: BadgerSystem):
    badger = badger_prod
    common_controller_params = DotMap(
        governance=badger.deployer,
        strategist=badger.deployer,
        keeper=badger.deployer,
        onesplit=registry.onesplit.contract,
        rewards=badger.dao.agent,
    )

    # ===== Confirm Controller =====

    # Native Controller
    params = common_controller_params

    params.setts = [
        [
            badger.token,
            badger.getSett("native.badger"),
            badger.getStrategy("native.badger"),
        ],
        [
            registry.curve.pools.sbtcCrv.token,
            badger.getSett("native.sbtcCrv"),
            badger.getStrategy("native.sbtcCrv"),
        ],
        [
            registry.curve.pools.renCrv.token,
            badger.getSett("native.renCrv"),
            badger.getStrategy("native.renCrv"),
        ],
        [
            registry.curve.pools.tbtcCrv.token,
            badger.getSett("native.tbtcCrv"),
            badger.getStrategy("native.tbtcCrv"),
        ],
    ]
    confirm_controller_params(badger.getController("native"), params)

    # Harvest Controller
    params = common_controller_params
    params.setts = [
        [
            registry.curve.pools.renCrv.token,
            badger.getSett("harvest.renCrv"),
            badger.getStrategy("harvest.renCrv"),
        ]
    ]
    confirm_controller_params(badger.getController("harvest"), params)

    # ===== Confirm Setts =====

    # Native Setts
    # TODO: Change governance and strategist to prod values
    common_native_sett_params = DotMap(
        governance=badger.deployer,
        strategist=AddressZero,
        keeper=badger.deployer,
        controller=badger.getController("native"),
        min=9500,
    )

    params = common_native_sett_params
    params.token = badger.token
    params.name = "Badger Sett Badger"
    params.symbol = "bBADGER"
    confirm_sett_params(badger.getSett("native.badger"), params)

    params = common_native_sett_params
    params.token = registry.curve.pools.sbtcCrv.token
    params.name = "Badger Sett Curve.fi renBTC/wBTC/sBTC"
    params.symbol = "bcrvRenWSBTC"
    confirm_sett_params(badger.getSett("native.sbtcCrv"), params)

    params = common_native_sett_params
    params.token = registry.curve.pools.renCrv.token
    params.name = "Badger Sett Curve.fi renBTC/wBTC"
    params.symbol = "bcrvRenWBTC"
    confirm_sett_params(badger.getSett("native.renCrv"), params)

    params = common_native_sett_params
    params.token = registry.curve.pools.tbtcCrv.token
    params.name = "Badger Sett Curve.fi tBTC/sbtcCrv"
    params.symbol = "btbtc/sbtcCrv"
    confirm_sett_params(badger.getSett("native.tbtcCrv"), params)

    # Harvest Setts
    harvest_sett_params = DotMap(
        governance=badger.deployer,
        strategist=AddressZero,
        keeper=badger.deployer,
        controller=badger.getController("harvest"),
        min=9500,
        token=registry.curve.pools.renCrv.token,
        name="Badger SuperSett (Harvest) Curve.fi renBTC/wBTC",
        symbol="bSupercrvRenWBTC",
    )
    confirm_sett_params(badger.getSett("harvest.renCrv"), harvest_sett_params)

    # ===== Confirm Strategies =====

    common_strategy_params = DotMap(
        governance=badger.deployer,
        strategist=badger.deployer,
        keeper=badger.keeper,
        controller=badger.getController("native"),
        guardian=badger.guardian,
        performanceFeeGovernance=1000,
        performanceFeeStrategist=1000,
        withdrawalFee=75,
    )

    # ===== Native Strategies =====

    # == Badger Native ==
    params = common_strategy_params
    params.name = "StrategyBadgerRewards"
    params.want = badger.token
    params.performanceFeeGovernance = 0
    params.performanceFeeStrategist = 0
    params.withdrawalFee = 0

    confirm_strategy_common_params(badger.getStrategy("native.badger"), params)

    confirm_strategy_badger_rewards_params(
        badger.getStrategy("native.badger"),
        DotMap(geyser=badger.getSettRewards("native.badger")),
    )

    # == Badger LP ==
    params = common_strategy_params
    params.name = "StrategyBadgerLpMetaFarm"
    params.want = badger.pair
    params.performanceFeeGovernance = 0
    params.performanceFeeStrategist = 0
    params.withdrawalFee = 0

    confirm_strategy_common_params(badger.getStrategy("native.uniBadgerWbtc"), params)

    confirm_strategy_badger_rewards_params(
        badger.getStrategy("native.uniBadgerWbtc"),
        DotMap(geyser=badger.getSettRewards("native.uniBadgerWbtc")),
    )

    # == Native SbtcCrv ==
    params = common_strategy_params
    params.name = "StrategyCurveGauge"
    params.want = registry.curve.pools.sbtcCrv.token
    params.performanceFeeGovernance = 1000
    params.performanceFeeStrategist = 1000
    params.withdrawalFee = 75

    confirm_strategy_common_params(badger.getStrategy("native.sbtcCrv"), params)

    params = common_strategy_params
    params.name = "StrategyCurveGauge"
    params.want = registry.curve.pools.renCrv.token
    params.performanceFeeGovernance = 1000
    params.performanceFeeStrategist = 1000
    params.withdrawalFee = 75

    confirm_strategy_common_params(badger.getStrategy("native.renCrv"), params)

    params = common_strategy_params
    params.name = "StrategyCurveGauge"
    params.want = registry.curve.pools.tbtcCrv.token
    params.performanceFeeGovernance = 1000
    params.performanceFeeStrategist = 1000
    params.withdrawalFee = 75

    confirm_strategy_common_params(badger.getStrategy("native.tbtcCrv"), params)

    # Harvest Strategies
    params.name = "StrategyHarvestMetaFarm"
    params.controller = badger.getController('harvest')
    params.want = registry.curve.pools.renCrv.token
    params.performanceFeeGovernance = 0
    params.performanceFeeStrategist = 0
    params.farmPerformanceFeeGovernance = 1000
    params.farmPerformanceFeeStrategist = 1000
    params.withdrawalFee = 75
    params.harvestVault = registry.harvest.vaults.renCrv
    params.vaultFarm = registry.harvest.farms.fRenCrv
    params.metaFarm = registry.harvest.farms.farm
    params.badgerTree = badger.badgerTree

    confirm_strategy_common_params(badger.getStrategy("harvest.renCrv"), params)
    confirm_strategy_harvest_meta_farm_params(
        badger.getStrategy("harvest.renCrv"), params
    )

    """
    def confirm_strategy_harvest_meta_farm_params(strategy, params):
    assert strategy.harvestVault() == params.harvestVault
    assert strategy.vaultFarm() == params.vaultFarm
    assert strategy.metaFarm() == params.metaFarm
    assert strategy.badgerTree() == params.badgerTree

    assert strategy.farm() == registry.harvest.farmToken
    assert strategy.depositHelper() == registry.harvest.depositHelper
    assert strategy.weth() == registry.tokens.weth

    assert (
        strategy.farmPerformanceFeeGovernance() == params.farmPerformanceFeeGovernance
    )
    assert (
        strategy.farmPerformanceFeeStrategist() == params.farmPerformanceFeeStrategist
    )
    """

    # Supporting Infrastructure: Rewards
    confirm_staking_rewards_params(
        badger.getSettRewards("native.badger"),
        DotMap(approvedStaker=badger.getStrategy("native.badger")),
    )

    confirm_staking_rewards_params(
        badger.getSettRewards("native.uniBadgerWbtc"),
        DotMap(approvedStaker=badger.getStrategy("native.uniBadgerWbtc")),
    )


# @pytest.mark.skip()
def test_confirm_setup_rewards(badger_prod):
    badger = badger_prod
    # Badger Tree
    confirm_badger_tree_params(
        badger,
        badger.badgerTree,
        DotMap(
            admin=badger.devMultisig,
            rootUpdater=badger.deployer,
            guardian=badger.deployer,
            initialBalance=badger.initialBadgerTreeBalance,
        ),
    )

    # Rewards Escrow
    confirm_rewards_escrow_params(
        badger.rewardsEscrow, DotMap(owner=badger.devMultisig)
    )

    # Badger Hunt
    confirm_badger_hunt_params(
        badger.badgerHunt,
        DotMap(
            token=badger.token,
            merkleRoot=EmptyBytes32,
            epochDuration=daysToSeconds(1),
            rewardReductionPerEpoch=2000,
            claimsStart=badger_config.huntParams.startTime,
            gracePeriod=daysToSeconds(2),
            rewardsEscrow=badger.rewardsEscrow,
            currentRewardRate=10000,
        ),
    )

    # Badger Geysers
    common_geyser_params = DotMap(
        tokenLockers=[badger.rewardsEscrow.address],
        admin=badger.devMultisig,
        initialDistributionToken=badger.token,
    )

    params = common_geyser_params
    params.stakingToken = badger.getSett("native.renCrv")
    confirm_badger_geyser_params(badger.getGeyser("native.renCrv"), params)

    params.stakingToken = badger.getSett("native.sbtcCrv")
    confirm_badger_geyser_params(badger.getGeyser("native.sbtcCrv"), params)

    params.stakingToken = badger.getSett("native.tbtcCrv")
    confirm_badger_geyser_params(badger.getGeyser("native.tbtcCrv"), params)

    params.stakingToken = badger.getSett("native.badger")
    confirm_badger_geyser_params(badger.getGeyser("native.badger"), params)

    params.stakingToken = badger.getSett("harvest.renCrv")
    confirm_badger_geyser_params(badger.getGeyser("harvest.renCrv"), params)

    # Ensure staking not possible
    for key, geyser in badger.geysers.items():
        with brownie.reverts("BadgerGeyser: Distribution not started"):
            geyser.stake(0, '0x', {'from': badger.deployer})
            geyser.stakeFor(0, '0x', badger.deployer, {'from': badger.deployer})

    # Badger Balances
    # Some of the initial supply is distributed to Sett special StakingRewards pools & BadgerTree
    assert (
        badger.token.balanceOf(badger.rewardsEscrow)
        == badger.initialRewardsEscrowBalance
    )

    assert (
        badger.token.balanceOf(badger.badgerHunt)
        == badger_config.huntParams.badgerAmount
    )

    assert (
        badger.token.balanceOf(badger.daoBadgerTimelock)
        == badger_config.tokenLockParams.badgerLockAmount
    )


# @pytest.mark.skip()
def test_confirm_setup_locking_infra(badger_prod):
    badger = badger_prod
    # DAO Timelock
    confirm_simple_timelock_params(
        badger.daoBadgerTimelock,
        DotMap(
            token=badger.token,
            beneficiary=badger.dao.agent,
            releaseTime=badger_config.globalStartTime
            + badger_config.tokenLockParams.lockDuration,
        ),
    )

    # Ops Team Smart Vesting
    confirm_smart_vesting_params(
        badger.teamVesting,
        DotMap(
            token=badger.token,
            beneficiary=badger.devMultisig,
            governor=badger.dao.agent,
            start=badger_config.teamVestingParams.startTime,
            duration=badger_config.teamVestingParams.totalDuration,
        ),
    )
