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

# seed random number generator
seed(1)


def sett_snapshot(sett, strategy, account):
    want = interface.IERC20(strategy.want())
    snapshot = DotMap(
        want=DotMap(contract=want, userBalance=want.balanceOf(account)),
        sett=DotMap(
            contract=sett,
            totalSupply=sett.totalSupply(),
            userBalance=sett.balanceOf(account),
            wantReserve=want.balanceOf(sett),
            available=sett.available(),
            balance=sett.balance(),
            # pricePerFullShare=sett.getPricePerFullShare()
        ),
        strategy=DotMap(
            contract=strategy,
            name=strategy.getName(),
            balanceOf=strategy.balanceOf(),
            balanceOfWant=strategy.balanceOfWant(),
            balanceOfPool=strategy.balanceOfPool(),
        ),
    )

    if sett.totalSupply() > 0:
        snapshot.sett.pricePerFullShare = sett.getPricePerFullShare()

    snapshot = add_strategy_components(snapshot)
    return snapshot


def add_strategy_components(snapshot):
    name = snapshot.strategy.name
    strategy = snapshot.strategy.contract

    result = snapshot

    if name == "StrategyPickleMetaFarm":
        pickle = interface.IERC20(strategy.pickle())
        pickleJar = interface.IPickleJar(strategy.pickleJar())
        pickleChef = interface.IPickleChef(strategy.pickleChef())
        stakingRewards = interface.IStakingRewards(strategy.pickleStaking())
        
        result.strategy.pickleBalance = pickle.balanceOf(strategy)
        result.strategy.pickleJar.stakedShares = pickleJar.balanceOf(strategy)
        result.strategy.pickleChef.stakedShares = pickleChef.userInfo(
            strategy.pid(), strategy
        )[0]
        result.strategy.stakingRewards.stakedPickle = stakingRewards.balanceOf(
            strategy
        )
        result.strategy.stakingRewards.earnedWeth = stakingRewards.earned(strategy)

    if name == "StrategyHarvestMetaFarm":
        farm = interface.IERC20(strategy.farm())
        harvestVault = interface.IHarvestVault(strategy.harvestVault())
        harvestVaultToken = interface.IERC20(strategy.harvestVault())
        vaultFarm = interface.IRewardPool(strategy.harvestVault())
        metaFarm = interface.IRewardPool(strategy.harvestVault())

        result.vaultFarm.contract = interface.IRewardPool(strategy.harvestVault())

        result.strategy.farmBalance = farm.balanceOf(strategy)

        result.strategy.harvestVault.stakedShares = harvestVault.balanceOf(strategy)
        result.strategy.harvestVault.stakedSharesInFarm = vaultFarm.balanceOf(strategy)
        result.strategy.harvestVault.pricePerFullShare = (
            harvestVault.getPricePerFullShare()
        )
        result.strategy.metaFarm.stakedFarm = metaFarm.balanceOf(strategy)
    return result


# def get_strategy_pool_balance(strategy):
#     strategyName = strategy.getName()

#     if strategyName == "StrategyCurveGauge":
#     if strategyName == "StrategyPickleMetaFarm":
#     if strategyName == "StrategyHarvestMetaFarm":
#     if strategyName == "StrategyBadgerLpMetaFarm":
#     if strategyName == "StrategyBadgerRewards":


def confirm_deposit(before, after, user, depositAmount):
    """
    Deposit Should;
    - Increase the totalSupply() of Sett tokens
    - Increase the balanceOf() Sett tokens for the user based on depositAmount / pricePerFullShare
    - Increase the balanceOf() want in the Sett by depositAmountt
    - Decrease the balanceOf() want of the user by depositAmountt
    """
    assert after.sett.totalSupply == before.sett.totalSupply + depositAmount
    assert after.sett.userBalance > before.sett.userBalance
    assert after.sett.wantReserve > before.sett.wantReserve
    assert after.want.userBalance < before.want.userBalance


def confirm_earn(before, after):
    """
    Earn Should:
    - Decrease the balanceOf() want in the Sett
    - Increase the balanceOf() want in the Strategy
    - Increase the balanceOfPool() in the Strategy
    - Reduce the balanceOfWant() in the Strategy to zero
    """
    assert after.sett.wantReserve <= before.sett.wantReserve
    assert after.strategy.balanceOfWant == 0
    assert after.strategy.balanceOfPool > before.strategy.balanceOfPool
    assert after.strategy.balanceOf > before.strategy.balanceOf


def confirm_withdraw(before, after, user):
    """
    Withdraw Should;
    - Decrease the totalSupply() of Sett tokens
    - Decrease the balanceOf() Sett tokens for the user based on withdrawAmount and pricePerFullShare
    - Decrease the balanceOf() want in the Strategy
    - Decrease the balance() tracked for want in the Strategy
    - Decrease the available() if it is not zero
    """
    assert after.sett.totalSupply < before.sett.totalSupply
    assert after.sett.userBalance < before.sett.userBalance
    assert after.sett.wantReserve <= before.sett.wantReserve
    assert after.strategy.balanceOfPool <= before.strategy.balanceOfPool
    assert after.strategy.balanceOfWant <= before.strategy.balanceOfWant

    assert (
        after.strategy.balanceOfWant
        + after.strategy.balanceOfPool
        + after.sett.wantReserve
        < before.strategy.balanceOfWant
        + before.strategy.balanceOfPool
        + before.sett.wantReserve
    )


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


def confirm_harvest_harvest(before, after):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Reduce the amount of idle FARM to zero
    - Reduce FARM in vaultFarm to zero
    - Reduce FARM in metaFarm to zero
    - Increase the ppfs on sett
    """

    assert after.strategy.farmBalance == 0
    # assert after.strategy.vaultFarm.contract.earned() == 0
    assert after.strategy.metaFarm.stakedFarm == 0


def confirm_harvest_pickle(before, after):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Reduce the amount of idle PICKLE to zero
    - Reduce PICKLE in pickleStaking to zero
    - Increase the ppfs on sett
    """
    assert after.strategy.balanceOf > before.strategy.balanceOf
    assert after.strategy.pickleBalance == 0
    assert (
        after.strategy.stakingRewards.stakedPickle
        > before.strategy.stakingRewards.stakedPickle
    )
    if before.sett.pricePerFullShare:
        assert after.sett.pricePerFullShare > before.sett.pricePerFullShare


def confirm_harvest_curve_gauge(before, after):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Increase the ppfs on sett
    """

    assert after.strategy.balanceOf > before.strategy.balanceOf
    if before.sett.pricePerFullShare:
        assert after.sett.pricePerFullShare > before.sett.pricePerFullShare


def confirm_harvest_badger_rewards(before, after):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Reduce the amount of idle BADGER to zero
    - Increase the ppfs on sett
    """

    assert after.strategy.balanceOf > before.strategy.balanceOf
    if before.sett.pricePerFullShare:
        assert after.sett.pricePerFullShare > before.sett.pricePerFullShare


def confirm_harvest_badger_lp(before, after):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Reduce the amount of idle BADGER to zero
    - Increase the ppfs on sett
    """

    assert after.strategy.balanceOf > before.strategy.balanceOf
    if before.sett.pricePerFullShare:
        assert after.sett.pricePerFullShare > before.sett.pricePerFullShare


def confirm_harvest(before, after, user):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Reduce the number of tended tokens in the Strategy to zero
    - Reduce the number of tended tokens staked in strategy-specific mechanism to zero
    """
    name = before.strategy.name

    if name == "StrategyHarvestMetaFarm":
        confirm_harvest_harvest(before, after)
    if name == "StrategyPickleMetaFarm":
        confirm_harvest_pickle(before, after)
    if name == "StrategyCurveGauge":
        confirm_harvest_curve_gauge(before, after)
    if name == "StrategyBadgerRewards":
        confirm_harvest_badger_rewards(before, after)
    if name == "StrategyBadgerLpMetaFarm":
        confirm_harvest_badger_lp(before, after)

