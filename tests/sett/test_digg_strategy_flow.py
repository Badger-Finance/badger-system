import pytest
from brownie import (
    accounts,
    chain,
    reverts,
)
from rich.console import Console

from helpers.time_utils import days
from helpers.constants import MaxUint256
from helpers.sett.DiggSnapshotManager import DiggSnapshotManager
from tests.conftest import badger_single_sett, diggSettTestConfig

console = Console()


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", diggSettTestConfig,
)
def test_single_user_harvest_flow(settConfig):
    badger = badger_single_sett(settConfig)

    sett = badger.getSett(settConfig["id"])
    strategy = badger.getStrategy(settConfig["id"])
    want = badger.getStrategyWant(settConfig["id"])

    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    snap = DiggSnapshotManager(badger, settConfig["id"])

    deployer = badger.deployer
    randomUser = accounts[6]

    tendable = strategy.isTendable()

    startingBalance = want.balanceOf(deployer)

    depositAmount = startingBalance // 2
    assert startingBalance >= depositAmount
    assert startingBalance >= 0

    # Deposit
    want.approve(sett, MaxUint256, {"from": deployer})
    snap.settDeposit(depositAmount, {"from": deployer})

    # Push/rebase on an exchange rate of 1.2 (DIGG trading at 1.2x BTC)
    snap.rebase(1.2 * 10 ** 18, {"from": deployer})

    # Earn
    snap.settEarn({"from": settKeeper})

    if tendable:
        with reverts("onlyAuthorizedActors"):
            strategy.tend({"from": randomUser})

        snap.settTend({"from": strategyKeeper})

    chain.sleep(days(0.5))
    chain.mine()

    # Push/rebase on an exchange rate of 0.6 (DIGG trading at 0.8x BTC)
    snap.rebase(0.6 * 10 ** 18, {"from": deployer})

    if tendable:
        snap.settTend({"from": strategyKeeper})

    chain.sleep(days(1))
    chain.mine()

    with reverts("onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    snap.settHarvest({"from": strategyKeeper})

    chain.sleep(days(1))
    chain.mine()

    # Push/rebase on an exchange rate of 1.6 (DIGG trading at 1.6x BTC)
    snap.rebase(1.6 * 10 ** 18, {"from": deployer})

    if tendable:
        snap.settTend({"from": strategyKeeper})

    snap.settWithdraw(depositAmount // 2, {"from": deployer})

    chain.sleep(days(3))
    chain.mine()

    # Push/rebase on an exchange rate of 0.7 (DIGG trading at 0.7x BTC)
    snap.rebase(0.7 * 10 ** 18, {"from": deployer})

    snap.settHarvest({"from": strategyKeeper})
    snap.settWithdraw(depositAmount // 2 - 1, {"from": deployer})

    assert False
