from operator import itemgetter
from tests.helpers import getTokenMetadata
from tests.sett.helpers.simulation import take_rewards_action

import brownie
import pytest
from brownie import *
from brownie.test import given, strategy
from dotmap import DotMap
from helpers.constants import *
from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from helpers.proxy_utils import deploy_proxy
from helpers.registry import whale_registry
from helpers.time_utils import daysToSeconds, hours
from scripts.deploy.deploy_badger import main
from tests.conftest import badger_single_sett
from tests.sett.helpers.snapshots import (
    confirm_deposit,
    confirm_earn,
    confirm_harvest,
    confirm_tend,
    confirm_withdraw,
    sett_snapshot,
)


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
def test_farming_flow_single_user(settId):
    """
    - A single user will deposit into Sett and stake for rewards
    - Keeper will take appropriate actions throughout
    - RewardsBot will calculate rewards
    - The user will claim rewards
    - The user will unstake 
    
    After unstake:
    - Rewards bot will continue, should calculate no new rewards (Will not publish any more roots)
    - User will withdraw

    After withdraw:
    - Rewards bot will continue, should calculate no new rewards
    - Keeper bot should take no actions

    """
    badger = badger_single_sett(settId)
    controller = badger.getController(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)
    farm = badger.getGeyser(settId)

    deployer = badger.deployer
    keeper = badger.keeper
    user = accounts[2]
    randomUser = accounts[6]

    depositAmount = Wei("1 ether")

    print(getTokenMetadata(want.address))
    assert want.balanceOf(deployer) >= depositAmount
    want.transfer(user, depositAmount, {"from": deployer})
    assert want.balanceOf(user) >= depositAmount

    assert sett.token() == strategy.want()
    want.approve(sett, MaxUint256, {"from": user})
    sett.deposit(depositAmount, {"from": user})
    chain.mine()

    globalStartTime = farm.globalStartTime()

    assert chain.time() > globalStartTime

    shares = sett.balanceOf(user)

    sett.earn({'from': keeper})
    chain.sleep(hours(2))

    chain.sleep(hours(6))
    chain.mine()

    sett.approve(farm, shares, {'from': user})

    farm.stake(shares, '0x', {'from': user})

    chain.sleep(hours(12))
    chain.mine()

    farm.unstake(shares / 2, '0x', {'from': user})

    chain.sleep(hours(12))
    chain.mine()

    # take_rewards_action(badger, chain.height, "rootUpdater")
    # take_rewards_action(badger, chain.height, "guardian")

    shares = sett.balanceOf(user)
    sett.approve(farm, shares, {'from': user})
    farm.stake(shares, '0x', {'from': user})
    chain.mine()

    take_rewards_action(badger, chain.height, "rootUpdater")
    # take_rewards_action(badger, chain.height, "guardian")

    

    

