from helpers.registry import Multicall
from scripts.systems.badger_system import BadgerSystem
import brownie
from helpers.proxy_utils import deploy_proxy
import pytest
from operator import itemgetter
from brownie.test import given, strategy
from brownie import *
from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from dotmap import DotMap
from scripts.deploy.deploy_badger import main
from random import seed
from random import random
from helpers.constants import *
from brownie.utils import color


def confirm_tend_harvest(before, after):
    """
    Tend Should:
    - Leave no FARM idle in the Strategy
    - Not change the staked shares in harvestVault
    - Increase the staked FARM in the metaFarm
    """

    assert after.strategy.farmBalance == 0
    assert (
        after.strategy.harvestVault.stakedShares
        == before.strategy.harvestVault.stakedShares
    )

    assert (
        after.strategy.harvestVault.stakedSharesInFarm
        == before.strategy.harvestVault.stakedSharesInFarm
    )

    # TODO: Re-enable after check
    # assert after.strategy.metaFarm.stakedFarm > before.strategy.metaFarm.stakedFarm


def confirm_tend_pickle(before, after):
    """
    Tend Should:
    - Leave no PICKLE idle in the Strategy
    - Not change the staked shares in pickleJar
    - Not change the staked shares in pickleChef
    - Increase the staked PICKLE in the stakingRewards
    - No WETH available for harvest from stakingRewards
    """
    print(after.strategy.pickleBalance)

    assert after.strategy.pickleBalance == 0
    assert (
        after.strategy.pickleJar.stakedShares == before.strategy.pickleJar.stakedShares
    )
    assert (
        after.strategy.pickleChef.stakedShares
        == before.strategy.pickleChef.stakedShares
    )
    assert (
        after.strategy.stakingRewards.stakedPickle
        > before.strategy.stakingRewards.stakedPickle
    )
    assert after.strategy.stakingRewards.earnedWeth == 0


def confirm_tend(before, after, user):
    """
    Tend Should;
    - Increase the number of staked tended tokens in the strategy-specific mechanism
    - Reduce the number of tended tokens in the Strategy to zero
    """
    name = before.strategy.name

    if name == "StrategyHarvestMetaFarm":
        confirm_tend_harvest(before, after)
    if name == "StrategyPickleMetaFarm":
        confirm_tend_pickle(before, after)


def confirm_harvest_curve_gauge(before, after):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Increase the ppfs on sett
    """

    assert after.strategy.balanceOf >= before.strategy.balanceOf
    if before.sett.pricePerFullShare:
        assert after.sett.pricePerFullShare > before.sett.pricePerFullShare


def confirm_migrate_curve_gauge(before, after):
    assert False


def confirm_migrate_badger_rewards(before, after):
    """
    Leave no Badger in StakingRewards or unharvested
    """
    assert False


def confirm_migrate_badger_lp(before, after):
    assert False


def confirm_migrate(before, after):
    """
    Migrate Should;
    - Increase the want asset in the Sett
    - Leave no want in the Strategy
    """
