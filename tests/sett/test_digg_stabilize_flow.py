import pytest
from brownie import *
from helpers.time_utils import days
from helpers.constants import MaxUint256
from helpers.sett.DiggStabilizerSnapshotManager import DiggStabilizerSnapshotManager
from tests.conftest import badger_single_sett, stabilizeTestConfig
from helpers.token_utils import distribute_from_whales

@pytest.mark.parametrize(
    "settConfig", stabilizeTestConfig,
)
def test_single_user_rebalance_flow(settConfig):
    badger = badger_single_sett(settConfig)

    sett = badger.vault
    strategy = badger.strategy
    controller = badger.controller

    want = interface.IDigg(strategy.want())

    print("Sett", sett.address)
    print("strategy", strategy.address)
    print("controller", controller.address)
    print("want", want.address)

    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    snap = DiggStabilizerSnapshotManager(badger, settConfig["id"])

    deployer = badger.deployer
    randomUser = accounts[6]

    distribute_from_whales(randomUser, 0.8, "digg")

    startingBalance = want.balanceOf(randomUser)

    depositAmount = startingBalance // 2
    assert startingBalance >= depositAmount
    assert startingBalance >= 0

    # Deposit
    want.approve(sett, MaxUint256, {"from": randomUser})
    snap.settDeposit(depositAmount, {"from": randomUser})

    chain.sleep(days(1))
    chain.mine()

    # Earn
    snap.settEarn({"from": settKeeper})

    chain.sleep(days(1))
    chain.mine()

    # Rebalance
    snap.rebalance({"from": settKeeper})

    assert False
