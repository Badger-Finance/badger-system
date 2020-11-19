from helpers.time_utils import daysToSeconds
from brownie import *
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from config.badger_config import badger_config

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

    assert sett.controller() == params.controller
    assert sett.token() == params.token
    assert sett.name() == params.name
    assert sett.symbol() == params.symbol

    assert sett.totalSupply() == 0
    assert sett.min() == params.min


def confirm_strategy_common_params(strategy, params):
    assert strategy.governance() == params.governance
    assert strategy.strategist() == params.strategist
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
    assert strategy.rewardsTree() == params.rewardsTree

    assert strategy.farm() == registry.harvest.farmToken
    assert strategy.depositHelper() == registry.harvest.depositHelper
    assert strategy.weth() == registry.tokens.weth

    assert (
        strategy.farmPerformanceFeeGovernance() == params.farmPerformanceFeeGovernance
    )
    assert (
        strategy.farmPerformanceFeeStrategist() == params.farmPerformanceFeeStrategist
    )
    assert strategy.lastHarvested() == 0


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
    assert timelock.duration() == params.duration


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


def confirm_badger_tree_params(tree, params):
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


def test_confirm_setup_sett(badger):
    common_controller_params = DotMap(
        governance=badger.deployer,
        strategist=badger.deployer,
        keeper=badger.deployer,
        onesplit=registry.onesplit.contract,
        rewards=badger.dao.agent,
    )

    # Native Controller
    params = common_controller_params
    params.setts = [
        [badger.token, badger.sett.native.badger, badger.sett.native.strategies.badger],
        [
            registry.curve.pools.sbtcCrv.token,
            badger.sett.native.sbtcCrv,
            badger.sett.native.strategies.sbtcCrv,
        ],
        [
            registry.curve.pools.renCrv.token,
            badger.sett.native.renCrv,
            badger.sett.native.strategies.renCrv,
        ],
        [
            registry.curve.pools.tbtcCrv.token,
            badger.sett.native.tbtcCrv,
            badger.sett.native.strategies.tbtcCrv,
        ],
    ]
    confirm_controller_params(badger.sett.native.controller, params)

    # Harvest Controller
    params = common_controller_params
    params.setts = [
        [
            registry.curve.pools.renCrv.token,
            badger.sett.harvest.renCrv,
            badger.sett.harvest.strategies.renCrv,
        ]
    ]
    confirm_controller_params(badger.sett.harvest.controller, params)

    # Pickle Controller
    params = common_controller_params
    params.setts = [
        [
            registry.curve.pools.renCrv.token,
            badger.sett.pickle.renCrv,
            badger.sett.pickle.strategies.renCrv,
        ]
    ]
    confirm_controller_params(badger.sett.pickle.controller, params)

    # Native Setts
    # TODO: Change governance and strategist to prod values
    common_native_sett_params = DotMap(
        governance=badger.deployer,
        strategist=AddressZero,
        keeper=badger.deployer,
        controller=badger.sett.native.controller,
        min=9500,
    )

    params = common_native_sett_params
    params.token = badger.token
    params.name = "Badger Sett badger"
    params.symbol = "bBadger"
    confirm_sett_params(badger.sett.native.badger, params)

    params = common_native_sett_params
    params.token = registry.curve.pools.sbtcCrv.token
    params.name = "Badger Sett sbtcCrv"
    params.symbol = "bSbtcCrv"
    confirm_sett_params(badger.sett.native.sbtcCrv, params)

    params = common_native_sett_params
    params.token = registry.curve.pools.renCrv.token
    params.name = "Badger Sett renCrv"
    params.symbol = "bRenCrv"
    confirm_sett_params(badger.sett.native.renCrv, params)

    params = common_native_sett_params
    params.token = registry.curve.pools.tbtcCrv.token
    params.name = "Badger Sett tbtcCrv"
    params.symbol = "bTbtcCrv"
    confirm_sett_params(badger.sett.native.tbtcCrv, params)

    # Harvest Setts
    harvest_sett_params = DotMap(
        governance=badger.deployer,
        strategist=AddressZero,
        keeper=badger.deployer,
        controller=badger.sett.harvest.controller,
        min=9500,
        token=registry.curve.pools.renCrv.token,
        name="Badger SuperSett renCrv (Harvest)",
        symbol="bSuperRenCrv (Harvest)",
    )
    confirm_sett_params(badger.sett.harvest.renCrv, harvest_sett_params)

    # Pickle Setts
    pickle_sett_params = DotMap(
        governance=badger.deployer,
        strategist=AddressZero,
        keeper=badger.deployer,
        controller=badger.sett.pickle.controller,
        min=9500,
        token=registry.curve.pools.renCrv.token,
        name="Badger SuperSett renCrv (Pickle)",
        symbol="bSuperRenCrv (Pickle)",
    )
    confirm_sett_params(badger.sett.pickle.renCrv, pickle_sett_params)

    common_strategy_params = DotMap(
        governance=badger.deployer,
        strategist=badger.deployer,
        keeper=badger.keeper,
        controller=badger.sett.native.controller,
        guardian=badger.guardian,
        performanceFeeGovernance=1000,
        performanceFeeStrategist=1000,
        withdrawalFee=75,
    )

    # Native Strategies
    params = common_strategy_params
    params.name = "StrategyBadgerRewards"
    params.want = badger.token
    params.performanceFeeGovernance = 0
    params.performanceFeeStrategist = 0
    params.withdrawalFee = 0

    confirm_strategy_common_params(badger.sett.native.strategies.badger, params)
    confirm_strategy_badger_rewards_params(
        badger.sett.native.strategies.badger,
        DotMap(geyser=badger.sett.rewards.badger),
    )

    params = common_strategy_params
    params.name = "StrategyCurveGauge"
    params.want = registry.curve.pools.sbtcCrv.token
    params.performanceFeeGovernance = 1000
    params.performanceFeeStrategist = 1000
    params.withdrawalFee = 75

    confirm_strategy_common_params(badger.sett.native.strategies.sbtcCrv, params)

    params = common_strategy_params
    params.name = "StrategyCurveGauge"
    params.want = registry.curve.pools.renCrv.token

    confirm_strategy_common_params(badger.sett.native.strategies.renCrv, params)

    params = common_strategy_params
    params.name = "StrategyCurveGauge"
    params.want = registry.curve.pools.tbtcCrv.token

    confirm_strategy_common_params(badger.sett.native.strategies.tbtcCrv, params)

    # Harvest Strategies

    # Pickle Strategies

    # Supporting Infrastructure: Rewards
    confirm_staking_rewards_params(
        badger.sett.rewards.badger,
        DotMap(approvedStaker=badger.sett.native.strategies.badger),
    )


def test_confirm_setup_rewards(badger):
    # Badger Tree
    confirm_badger_tree_params(
        badger.badgerTree,
        DotMap(
            admin=badger.devMultisig,
            rootUpdater=badger.deployer,
            guardian=badger.deployer,
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
            gracePeriod=daysToSeconds(1),
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
    params.stakingToken = badger.sett.native.renCrv
    confirm_badger_geyser_params(badger.pools.sett.native.renCrv, params)

    params.stakingToken = badger.sett.native.sbtcCrv
    confirm_badger_geyser_params(badger.pools.sett.native.sbtcCrv, params)

    params.stakingToken = badger.sett.native.tbtcCrv
    confirm_badger_geyser_params(badger.pools.sett.native.tbtcCrv, params)

    params.stakingToken = badger.sett.native.badger
    confirm_badger_geyser_params(badger.pools.sett.native.badger, params)

    params.stakingToken = badger.sett.pickle.renCrv
    confirm_badger_geyser_params(badger.pools.sett.pickle.renCrv, params)

    params.stakingToken = badger.sett.harvest.renCrv
    confirm_badger_geyser_params(badger.pools.sett.harvest.renCrv, params)

    # Badger Balances
    assert (
        badger.token.balanceOf(badger.rewardsEscrow)
        == badger_config.rewardsEscrowBadgerAmount
    )

    assert (
        badger.token.balanceOf(badger.badgerHunt)
        == badger_config.huntParams.badgerAmount
    )

    assert (
        badger.token.balanceOf(badger.daoBadgerTimelock)
        == badger_config.tokenLockParams.badgerLockAmount
    )


def test_confirm_setup_locking_infra(badger):
    # DAO Timelock
    confirm_simple_timelock_params(
        badger.daoBadgerTimelock,
        DotMap(
            token=badger.token,
            beneficiary=badger.dao.agent,
            duration=badger_config.tokenLockParams.lockDuration,
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
