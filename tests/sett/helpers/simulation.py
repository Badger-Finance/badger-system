from tests.sett.helpers.snapshots import sett_snapshot
from tests.sett.strategy_test_config import (
    confirm_deposit,
    confirm_earn,
    confirm_harvest,
    confirm_tend,
    confirm_withdraw,
)
from tests.conftest import (
    distribute_from_whales,
    distribute_rewards_escrow,
    get_sett_by_id,
)
from helpers.time_utils import daysToSeconds
import brownie
from helpers.proxy_utils import deploy_proxy
import pytest
from operator import itemgetter
from brownie.test import given, strategy
from brownie import *
from helpers.constants import *
from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from dotmap import DotMap
from scripts.deploy.deploy_badger import main
from helpers.registry import whale_registry
from random import seed
from random import random


def record_action(record, action, after, timestamp):
    record[timestamp] = {"action": action, "after": after}


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


def get_random_within_balance(token, user):
    balance = token.balanceOf(user)


def take_user_action(sett, strategy, user):
    do_action = random()
    if do_action < 0.90:
        return "NoOp"

    action = random()

    # No Sett tokens? Only can deposit
    if sett.balanceOf(user) == 0 or action < 0.50:
        want = interface.IERC20(strategy.want())

        if want.balanceOf(user) == 0:
            return "NoOp"

        else:
            want.approve(sett, MaxUint256, {"from": user})
            sett.deposit()
            return "Deposit"

    else:
        withdrawable = sett.balanceOf(user)
        if withdrawable == 0:
            return "NoOp"
        else:
            to_withdraw = int(withdrawable * random())
            sett.withdraw(to_withdraw, {"from": user})
            return "Deposit"
