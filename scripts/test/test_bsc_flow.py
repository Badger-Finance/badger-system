from helpers.token_utils import distribute_test_ether
import brownie
import decouple
import pytest
from brownie import *
from helpers.constants import *
from helpers.proxy_utils import deploy_proxy
from helpers.registry import registry
from helpers.sett.SnapshotManager import SnapshotManager
from helpers.time_utils import days
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from tests.conftest import badger_single_sett, settTestConfig
from tests.helpers import distribute_from_whales

console = Console()


def setup_badger(badger: BadgerSystem, settConfig):
    controller = badger.getController("native")
    console.print(registry.pancake.chefPids.bnbBtcb)
    strategyLogic = StrategyPancakeLpOptimizer.deploy({"from": badger.deployer})

    strategy = deploy_proxy(
        "StrategyPancakeLpOptimizer",
        StrategyPancakeLpOptimizer.abi,
        strategyLogic.address,
        badger.devProxyAdmin.address,
        strategyLogic.initialize.encode_input(
            badger.devMultisig,
            badger.deployer,
            controller,
            badger.keeper,
            badger.guardian,
            [
                registry.pancake.chefPairs.bnbBtcb,
                registry.tokens.btcb,
                registry.tokens.bnb,
            ],
            [100, 100, 50],
            15,
        ),
        badger.deployer,
    )

    want = interface.IERC20(registry.pancake.chefPairs.bnbBtcb)
    multi = accounts.at(badger.devMultisig.address, force=True)

    controller.approveStrategy(want, strategy, {"from": multi})
    controller.setStrategy(want, strategy, {"from": multi})

    badger.setStrategy(settConfig["id"], strategy)
    snap = SnapshotManager(badger, settConfig["id"])

    table = []

    table.append(["want", strategy.want()])
    table.append(["token0", strategy.token0()])
    table.append(["token1", strategy.token1()])
    table.append(["wantPid", strategy.wantPid()])
    table.append(["performanceFeeGovernance", strategy.performanceFeeGovernance()])
    table.append(["performanceFeeStrategist", strategy.performanceFeeStrategist()])
    table.append(["withdrawalFee", strategy.withdrawalFee()])

    print(tabulate(table, headers=["param", "value"]))


def test_deposit_withdraw_single_user_flow(badger, settConfig, user):
    controller = badger.getController("native")
    strategy = badger.getStrategy(settConfig["id"])

    want = interface.IERC20(registry.pancake.chefPairs.bnbBtcb)

    snap = SnapshotManager(badger, settConfig["id"])

    sett = badger.getSett(settConfig["id"])
    strategist = badger.deployer

    settKeeper = accounts.at(sett.keeper(), force=True)

    randomUser = accounts[6]

    # Deposit
    assert want.balanceOf(user) > 0

    depositAmount = int(want.balanceOf(user) * 0.8)
    assert depositAmount > 0

    want.approve(sett, MaxUint256, {"from": user})
    # sett.deposit(depositAmount, {"from": deployer})
    snap.settDeposit(depositAmount, {"from": user})

    # Earn
    # with brownie.reverts("onlyAuthorizedActors"):
    #     sett.earn({"from": randomUser})

    min = sett.min()
    max = sett.max()
    remain = max - min

    # sett.earn({"from": settKeeper})
    snap.settEarn({"from": settKeeper})

    chain.sleep(15)
    chain.mine(1)

    snap.settWithdraw(depositAmount // 2, {"from": user})

    chain.sleep(10000)
    chain.mine(1)

    snap.settWithdraw(depositAmount // 2 - 1, {"from": user})


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


def main():
    badger = connect_badger()
    user = accounts[0]
    distribute_test_ether(user, Wei("10 ether"))
    distribute_from_whales(user)
    settConfig = {"id": "native.pancakeBnbBtcb"}
    setup_badger(badger, settConfig)
    test_deposit_withdraw_single_user_flow(badger, settConfig, user)
    # test_single_user_harvest_flow(badger, settConfig)
