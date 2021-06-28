import pytest
from brownie import *
from helpers.constants import *
from tests.conftest import settTestConfig

from tests.sett.generic_strategy_tests.strategy_flow import (
    assert_deposit_withdraw_single_user_flow,
    assert_single_user_harvest_flow,
    assert_migrate_single_user,
    assert_withdraw_other,
    assert_single_user_harvest_flow_remove_fees,
)

# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig", settTestConfig,
)
def test_deposit_withdraw_single_user_flow(settConfig):
    assert_deposit_withdraw_single_user_flow(settConfig)

    # assert False


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

    tendable = strategy.isTendable()

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
    snap.settEarn({"from": settKeeper})

    chain.sleep(days(1))
    chain.mine()

    if tendable:
        with brownie.reverts("onlyAuthorizedActors"):
            strategy.tend({"from": randomUser})

        snap.settTend({"from": strategyKeeper})

    chain.sleep(days(0.5))
    chain.mine()

    if tendable:
        snap.settTend({"from": strategyKeeper})

    chain.sleep(days(1))
    chain.mine()

    with brownie.reverts("onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    snap.settHarvest({"from": strategyKeeper})

    chain.sleep(days(1))
    chain.mine()

    if tendable:
        snap.settTend({"from": strategyKeeper})

    snap.settWithdraw(depositAmount // 2, {"from": deployer})

    chain.sleep(days(3))
    chain.mine()

    snap.settHarvest({"from": strategyKeeper})
    snap.settWithdraw(depositAmount // 2 - 1, {"from": deployer})

    assert False


@pytest.mark.skip()
@pytest.mark.parametrize("settConfig", settTestConfig)
def test_migrate_single_user(settConfig):
    assert_migrate_single_user(settConfig)


@pytest.mark.skip()
@pytest.mark.parametrize("settConfig", settTestConfig)
def test_withdraw_other(settConfig):
    assert_withdraw_other(settConfig)


@pytest.mark.skip()
@pytest.mark.parametrize("settConfig", settTestConfig)
def test_single_user_harvest_flow_remove_fees(settConfig):
    assert_single_user_harvest_flow_remove_fees(settConfig)
