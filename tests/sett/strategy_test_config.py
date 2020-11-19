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

# seed random number generator
seed(1)

strat_configs = DotMap(
    StrategyCurveGauge=DotMap(tendable=False),
    StrategyPickleMetaFarm=DotMap(tendable=True),
    StrategyHarvestMetaFarm=DotMap(tendable=True),
    StrategyBadgerLpMetaFarm=DotMap(tendable=False),
    StrategyBadgerRewards=DotMap(tendable=False),
)


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
    assert after.sett.wantReserve < before.sett.wantReserve
    assert after.strategy.balanceOf > before.strategy.balanceOf
    assert after.strategy.balanceOfPool > before.strategy.balanceOfPool
    assert after.strategy.balanceOfWant == 0


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
    
    assert after.strategy.balanceOfWant + after.strategy.balanceOfPool + after.sett.wantReserve < before.strategy.balanceOfWant + before.strategy.balanceOfPool + before.sett.wantReserve


def confirm_tend(before, after, user, withdrawAmount):
    """
    Tend Should;
    - Increase the number of staked tended tokens in the strategy-specific mechanism
    - Reduce the number of tended tokens in the Strategy to zero
    """
    assert False


def confirm_harvest(before, after, user, withdrawAmount):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Reduce the number of tended tokens in the Strategy to zero
    - Reduce the number of tended tokens staked in strategy-specific mechanism to zero
    """
    assert False


def take_keeper_action(sett, strategy, keeper):
    tendable = strategy.isTendable()

    if tendable:
        do_action = random()
        if do_action < 0.3:
            return "NoOp"
        if do_action < 0.7:
            strategy.tend({"from": keeper})
            return "Tend"
        else:
            strategy.harvest({"from": keeper})
            return "Harvest"

    else:
        do_action = random()
        if do_action < 0.7:
            return "NoOp"
        else:
            strategy.harvest({"from": keeper})
            return "Harvest"


def take_user_action(sett, strategy, user):
    do_action = random()
    if do_action < 0.90:
        return "NoOp"

    action = random()

    # No Sett tokens? Only can deposit
    if sett.balanceOf(user) == 0 or action < 0.50:
        want = interface.IERC20(strategy.want())
        want.approve(sett, MaxUint256, {"from": user})
        sett.deposit()
        return "Deposit"

    else:
        withdrawable = sett.balanceOf(user)
        to_withdraw = int(withdrawable * random())
        sett.withdraw(to_withdraw, {"from": user})
        return "Deposit"
