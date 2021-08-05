from helpers.time_utils import days
import brownie
from brownie import *
from helpers.constants import *
from helpers.sett.SnapshotManager import SnapshotManager
from tests.conftest import badger_single_sett


def assert_deposit_withdraw_single_user_flow(settConfig):
    badger = badger_single_sett(settConfig)

    sett = badger.getSett(settConfig["id"])
    want = badger.getStrategyWant(settConfig["id"])
    deployer = badger.deployer

    settKeeper = accounts.at(sett.keeper(), force=True)

    snap = SnapshotManager(badger, settConfig["id"])

    randomUser = accounts[6]

    print("== Testing == ", settConfig["id"], want.address)
    # Deposit
    assert want.balanceOf(deployer) > 0

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

    snap.settEarn({"from": settKeeper})

    chain.sleep(15)
    chain.mine(1)

    snap.settWithdraw(depositAmount // 2, {"from": deployer})

    chain.sleep(10000)
    chain.mine(1)

    snap.settWithdraw(depositAmount // 2 - 1, {"from": deployer})


def assert_single_user_harvest_flow(settConfig):
    badger = badger_single_sett(settConfig)

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


def assert_migrate_single_user(settConfig):
    badger = badger_single_sett(settConfig)
    controller = badger.getController(settConfig["id"])
    sett = badger.getSett(settConfig["id"])
    strategy = badger.getStrategy(settConfig["id"])
    want = badger.getStrategyWant(settConfig["id"])
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    deployer = badger.deployer
    randomUser = accounts[6]

    snap = SnapshotManager(badger, settConfig["id"])

    startingBalance = want.balanceOf(deployer)
    depositAmount = startingBalance // 2
    assert startingBalance >= depositAmount

    # Deposit
    want.approve(sett, MaxUint256, {"from": deployer})
    snap.settDeposit(depositAmount, {"from": deployer})

    chain.sleep(15)
    chain.mine()

    sett.earn({"from": strategyKeeper})

    chain.snapshot()

    # Test no harvests
    chain.sleep(days(2))
    chain.mine()

    before = {"settWant": want.balanceOf(sett), "stratWant": strategy.balanceOf()}

    with brownie.reverts():
        controller.withdrawAll(strategy.want(), {"from": randomUser})

    controller.withdrawAll(strategy.want(), {"from": deployer})

    after = {"settWant": want.balanceOf(sett), "stratWant": strategy.balanceOf()}

    assert after["settWant"] > before["settWant"]
    assert after["stratWant"] < before["stratWant"]
    assert after["stratWant"] == 0

    # Test tend only
    if strategy.isTendable():
        chain.revert()

        chain.sleep(days(2))
        chain.mine()

        strategy.tend({"from": strategyKeeper})

        before = {"settWant": want.balanceOf(sett), "stratWant": strategy.balanceOf()}

        with brownie.reverts():
            controller.withdrawAll(strategy.want(), {"from": randomUser})

        controller.withdrawAll(strategy.want(), {"from": deployer})

        after = {"settWant": want.balanceOf(sett), "stratWant": strategy.balanceOf()}

        assert after["settWant"] > before["settWant"]
        assert after["stratWant"] < before["stratWant"]
        assert after["stratWant"] == 0

    # Test harvest, with tend if tendable
    chain.revert()

    chain.sleep(days(1))
    chain.mine()

    if strategy.isTendable():
        strategy.tend({"from": strategyKeeper})

    chain.sleep(days(1))
    chain.mine()

    before = {
        "settWant": want.balanceOf(sett),
        "stratWant": strategy.balanceOf(),
        "rewardsWant": want.balanceOf(controller.rewards()),
    }

    with brownie.reverts():
        controller.withdrawAll(strategy.want(), {"from": randomUser})

    controller.withdrawAll(strategy.want(), {"from": deployer})

    after = {"settWant": want.balanceOf(sett), "stratWant": strategy.balanceOf()}

    assert after["settWant"] > before["settWant"]
    assert after["stratWant"] < before["stratWant"]
    assert after["stratWant"] == 0


def assert_withdraw_other(settConfig):
    """
    - Controller should be able to withdraw other tokens
    - Controller should not be able to withdraw core tokens
    - Non-controller shouldn't be able to do either
    """
    badger = badger_single_sett(settConfig)
    controller = badger.getController(settConfig["id"])
    sett = badger.getSett(settConfig["id"])
    strategy = badger.getStrategy(settConfig["id"])
    want = badger.getStrategyWant(settConfig["id"])

    deployer = badger.deployer
    randomUser = accounts[6]
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    startingBalance = want.balanceOf(deployer)

    depositAmount = Wei("1 ether")

    assert startingBalance >= depositAmount

    # Deposit
    want.approve(sett, MaxUint256, {"from": deployer})
    sett.deposit(depositAmount, {"from": deployer})

    chain.sleep(15)
    chain.mine()

    sett.earn({"from": strategyKeeper})

    chain.sleep(days(0.5))
    chain.mine()

    if strategy.isTendable():
        strategy.tend({"from": strategyKeeper})
    ## Extra sleep because some tend will actually swap
    chain.sleep(days(1))
    chain.mine()
    strategy.harvest({"from": strategyKeeper})

    chain.sleep(days(0.5))
    chain.mine()

    mockAmount = Wei("1000 ether")
    mockToken = MockToken.deploy({"from": deployer})
    mockToken.initialize([strategy], [mockAmount], {"from": deployer})

    assert mockToken.balanceOf(strategy) == mockAmount

    # Should not be able to withdraw protected tokens
    protectedTokens = strategy.getProtectedTokens()
    for token in protectedTokens:
        with brownie.reverts():
            controller.inCaseStrategyTokenGetStuck(
                strategy, token, {"from": strategyKeeper}
            )

    # Should send balance of non-protected token to sender
    controller.inCaseStrategyTokenGetStuck(strategy, mockToken, {"from": deployer})

    with brownie.reverts():
        controller.inCaseStrategyTokenGetStuck(
            strategy, mockToken, {"from": randomUser}
        )

    assert mockToken.balanceOf(controller) == mockAmount


def assert_single_user_harvest_flow_remove_fees(settConfig):
    suiteName = "assert_single_user_harvest_flow_remove_fees" + ": " + settConfig["id"]

    badger = badger_single_sett(settConfig)
    controller = badger.getController(settConfig["id"])
    sett = badger.getSett(settConfig["id"])
    strategy = badger.getStrategy(settConfig["id"])
    want = badger.getStrategyWant(settConfig["id"])

    deployer = badger.deployer
    randomUser = accounts[6]

    snap = SnapshotManager(badger, settConfig["id"])

    tendable = strategy.isTendable()

    startingBalance = want.balanceOf(deployer)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    depositAmount = Wei("1 ether")
    assert startingBalance >= depositAmount

    # Deposit
    want.approve(sett, MaxUint256, {"from": deployer})
    sett.deposit(depositAmount, {"from": deployer})

    # Earn
    sett.earn({"from": strategyKeeper})

    chain.sleep(days(0.5))
    chain.mine()

    if tendable:
        tx = snap.settTend({"from": strategyKeeper})

    chain.sleep(days(1))
    chain.mine()

    with brownie.reverts("onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    snap.settHarvest({"from": strategyKeeper})

    # Harvesting on the HarvestMetaFarm does not increase the underlying position, it sends rewards to the rewardsTree
    # For HarvestMetaFarm, we expect FARM rewards to be distributed to rewardsTree
    assert want.balanceOf(controller.rewards()) > 0

    chain.sleep(days(1))
    chain.mine()

    if tendable:
        tx = strategy.tend({"from": strategyKeeper})

    chain.sleep(days(3))
    chain.mine()

    tx = snap.settHarvest({"from": strategyKeeper})

    sett.withdrawAll({"from": deployer})

    endingBalance = want.balanceOf(deployer)

    report = {
        "time": "4 days",
        "gains": endingBalance - startingBalance,
        "gainsPercentage": (endingBalance - startingBalance) / startingBalance,
    }

    print(report)
