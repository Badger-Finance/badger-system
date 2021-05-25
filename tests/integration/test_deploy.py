from helpers.time_utils import days
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
