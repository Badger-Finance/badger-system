from tests.helpers import distribute_test_assets
from tests.sett.helpers.simulation import (
    get_random_action_interval,
    get_random_deposit_amount,
    get_random_user,
    is_past_keeper_action_threshold,
    is_past_rewards_bot_action_threshold,
    take_keeper_action,
    take_rewards_action,
    take_user_action,
)
from tests.sett.helpers.snapshots import (
    confirm_deposit,
    confirm_earn,
    confirm_harvest,
    confirm_tend,
    confirm_withdraw,
    sett_snapshot,
)
from brownie.network.event import _decode_logs
from tests.conftest import badger_single_sett
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
from scripts.deploy.deploy_badger_with_actions import distribute_assets_to_users


@pytest.mark.parametrize(
    "settId",
    [
        "native.renCrv",
        # "native.badger",
        # "native.sbtcCrv",
        # "native.tbtcCrv",
        # "pickle.renCrv",
        # "harvest.renCrv",
    ],
)
def test_single_sett_simulation(settId):
    """
    - A set of actors will take randomized actions on Setts & rewards mechanisms (Deposit, Withdraw, Stake bTokens, Harvest rewards)
    Keeper will perform it's 
    Invariants will be checked between each action
    """
    startTime = chain.time()

    lastKeeperAction = startTime
    lastRewardsAction = startTime

    startBlock = chain.height

    badger = badger_single_sett(settId)
    controller = badger.getController(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    geyser = badger.getGeyser(settId)
    want = badger.getStrategyWant(settId)

    deployer = badger.deployer
    randomUser = accounts[6]

    assert sett.token() == strategy.want()
    assert geyser.getStakingToken() == sett

    distribute_assets_to_users(
        badger, [accounts[2], accounts[3], accounts[4]], distributePair=False
    )
    users = [badger.deployer, accounts[2], accounts[3], accounts[4]]

    # Initial deposit
    print("want", want, geyser)
    user = get_random_user(users)
    print("user", user)
    balance = want.balanceOf(user)
    amount = get_random_deposit_amount(balance)

    want.balanceOf(user)
    want.approve(sett, amount, {"from": user})
    sett.deposit(amount, {"from": user})
    chain.mine()
    sett.transfer(randomUser, amount // 2, {"from": user})
    assert sett.balanceOf(randomUser) == amount // 2
    sett.transfer(user, amount // 2, {"from": randomUser})
    actionEndBlock = chain.height
    rounds = 5

    for round in range(rounds):
        actionStartTime = chain.time()
        user = get_random_user(users)
        action = take_user_action(sett, strategy, geyser, user)
        print("user action", action, user, actionStartTime, want.balanceOf(user))
        chain.sleep(get_random_action_interval())
        chain.mine()

        # After each action check if we have should run keeper bots
        actionEndTime = chain.time()
        actionEndBlock = chain.height

        if is_past_keeper_action_threshold(lastKeeperAction, actionEndTime):
            lastKeeperAction = take_keeper_action(sett, strategy, badger.keeper)

    lastRewardsAction = take_rewards_action(
        badger, actionEndBlock, "rootUpdater"
    )
    lastRewardsAction = take_rewards_action(badger, actionEndBlock, "guardian")

    # Release founder rewards
    # DAO Approves founder to stake
    assert False
