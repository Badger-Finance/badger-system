from operator import itemgetter
from random import random, seed, choice

import brownie
import pytest
from assistant.rewards.rewards_assistant import run_action
from brownie import *
from brownie.test import given, strategy
from dotmap import DotMap
from scripts.systems.badger_system import BadgerSystem
from tests.sett.helpers.snapshots import sett_snapshot

from helpers.constants import *
from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from helpers.proxy_utils import deploy_proxy
from helpers.registry import whale_registry
from helpers.time_utils import daysToSeconds, hours


def record_action(record, action, after, timestamp):
    record[timestamp] = {"action": action, "after": after}


def run_rewards_bot():
    return


def run_keeper_bot():
    return


def get_random_user(users):
    return choice(users)


def get_random_in_range(max):
    return int(random() * max)


def get_random_deposit_amount(balance):
    roll = random()

    # 5% chance to go all in
    if roll < 0.05:
        return balance
    # Return random value sfrom 0 to balance
    else:
        return int(balance * random())


def do_sett_action(badger: BadgerSystem, id, user, action):
    sett = badger.getSett(id)
    geyser = badger.getGeyser(id)

    if action.type == "Deposit":
        sett.deposit(action.balance, {"from": user})
    if action.type == "Withdraw":
        sett.withdraw(action.balance, {"from": user})
    if action.type == "Stake":
        geyser.stake(action.balance, "", {"from": user})
    if action.type == "Unstake":
        geyser.unstake(action.balance, "", {"from": user})
    if action.type == "ClaimRewards":
        # badgerTree.claim(action.merkleProof)
        return


def get_random_action_interval():
    max = hours(6)
    return int(random() * max)


def is_past_keeper_action_threshold(lastActionTime, currentTime):
    return currentTime > lastActionTime + hours(24)


def is_past_rewards_bot_action_threshold(lastActionTime, currentTime):
    return currentTime > lastActionTime + hours(2)


def take_rewards_action(badger, endBlock, action):
    """
    Check rewards, pulling from events & badger config
    """
    result = run_action(badger, {"endBlock": endBlock, "action": action})
    chain.sleep(30)
    chain.mine()
    return chain.time()


def take_keeper_action(sett, strategy, keeper):
    """
    - earn() if sufficent new deposits
    - tend() if tending is profitable
    - harvest() if harvesting makes sense
    """
    tendable = strategy.isTendable()
    sett.earn({"from": keeper})
    print("earn", sett)
    chain.sleep(hours(4))
    chain.mine()

    if tendable:
        strategy.tend({"from": keeper})
        chain.mine()

    strategy.harvest({"from": keeper})
    print("harvest", sett)
    chain.mine()
    return chain.time()


def take_user_action(sett, strategy, geyser, user):
    do_action = random()
    if do_action < 0.5:
        return "NoOp"

    action = random()
    want = interface.IERC20(strategy.want())
    balance = want.balanceOf(user)
    settBalance = sett.balanceOf(user)

    # Deposit (No Sett tokens? Only can deposit)
    if settBalance == 0 or action < 0.30:
        if balance == 0:
            return "NoOp"

        else:
            allowance = want.allowance(user, sett)
            if allowance < balance:
                want.approve(sett, MaxUint256, {"from": user})
            sett.deposit(get_random_deposit_amount(balance), {"from": user})
            return "Deposit"

    # Stake
    if settBalance > 0 and action < 0.65:
        allowance = want.allowance(user, geyser)
        if allowance < settBalance:
            sett.approve(geyser, MaxUint256, {"from": user})
        chain.sleep(15)
        chain.mine()
        geyser.stake(get_random_deposit_amount(settBalance), "0x", {'from': user})
        return "Stake"
    # Unstake
    if geyser.totalStakedFor(user) > 0 and action < 0.80:
        staked = geyser.totalStakedFor(user)
        geyser.unstake(get_random_deposit_amount(staked), "0x", {'from': user})
        return "Unstake"
    # Withdraw
    elif settBalance > 0:
        withdrawable = sett.balanceOf(user)
        if withdrawable == 0:
            return "NoOp"
        else:
            sett.withdraw(get_random_in_range(withdrawable), {"from": user})
            return "Withdraw"
