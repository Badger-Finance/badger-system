from helpers.time_utils import days, hours
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.sett.SnapshotManager import SnapshotManager
from tests.conftest import badger_single_sett, settTestConfig
from tests.helpers import distribute_from_whales, getTokenMetadata
from tests.test_recorder import EventRecord, TestRecorder
from rich.console import Console

console = Console()

# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_deposit_withdraw_single_user_flow(settConfig):
    badger = badger_single_sett(settConfig)

    controller = badger.getController(settConfig["id"])
    sett = badger.getSett(settConfig["id"])
    strategy = badger.getStrategy(settConfig["id"])
    want = badger.getStrategyWant(settConfig["id"])

    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    snap = SnapshotManager(badger, settConfig["id"])

    deployer = badger.deployer

    governance = strategy.governance()

    randomUser = accounts[6]

    distribute_from_whales(deployer)
    
    assert want.balanceOf(deployer) >= 0

    depositAmount = int(want.balanceOf(deployer) * 0.8)
    assert depositAmount > 0

    want.approve(sett, MaxUint256, {"from": deployer})
    snap.settDeposit(depositAmount, {"from": deployer})

    # Earn
    with brownie.reverts("onlyAuthorizedActors"):
        sett.earn({"from": randomUser})

    min = sett.min()
    max = sett.max()
    remain = max - min

    #snap.settEarn({"from": settKeeper})

    chain.sleep(15)
    chain.mine(1)

    snap.settWithdraw(depositAmount // 2, {"from": deployer})

    chain.sleep(10000)
    chain.mine(1)

    snap.settWithdraw(depositAmount // 2 - 1, {"from": deployer})

    assert False

# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_single_user_harvest_flow(settConfig):
    badger = badger_single_sett(settConfig)

    controller = badger.getController(settConfig["id"])
    sett = badger.getSett(settConfig["id"])
    strategy = badger.getStrategy(settConfig["id"])
    want = badger.getStrategyWant(settConfig["id"])

    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    snap = SnapshotManager(badger, settConfig["id"])

    deployer = badger.deployer
    randomUser = accounts[6]

    distribute_from_whales(deployer)

    startingBalance = want.balanceOf(deployer)

    depositAmount = startingBalance // 2
    assert startingBalance >= depositAmount
    assert startingBalance >= 0

    # Deposit
    want.approve(sett, MaxUint256, {"from": deployer})
    snap.settDeposit(depositAmount, {"from": deployer})

    assert want.balanceOf(sett) > 0
    print("want.balanceOf(sett)", want.balanceOf(sett))

    # Earn
    #snap.settEarn({"from": settKeeper})

    chain.sleep(days(0.5))
    chain.mine()

    chain.sleep(days(1))
    chain.mine()

    with brownie.reverts("onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    snap.settHarvest({"from": strategyKeeper})

    chain.sleep(days(1))
    chain.mine()

    snap.settWithdraw(depositAmount // 2, {"from": deployer})

    chain.sleep(days(3))
    chain.mine()

    snap.settHarvest({"from": strategyKeeper})
    snap.settWithdraw(depositAmount // 2 - 1, {"from": deployer})

    assert False