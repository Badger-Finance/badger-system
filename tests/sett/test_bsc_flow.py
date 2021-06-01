from helpers.token_utils import distribute_test_ether
import brownie
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


class RevertException(Exception):
    def __init__(self, error, tx):
        self.error = error
        self.tx = tx


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

    token0 = registry.tokens.btcb
    token1 = registry.tokens.bnb
    cake = registry.pancake.cake

    strategy.setTokenSwapPath(cake, token0, [cake, token0], {"from": badger.deployer})
    strategy.setTokenSwapPath(cake, token1, [cake, token1], {"from": badger.deployer})

    # want = interface.IERC20(registry.pancake.chefPairs.bnbBtcb)
    # multi = accounts.at(badger.devMultisig.address, force=True)

    # snap = SnapshotManager(badger, settConfig["id"])

    table = []

    table.append(["want", strategy.want()])
    table.append(["token0", strategy.token0()])
    table.append(["token1", strategy.token1()])
    table.append(["wantPid", strategy.wantPid()])
    table.append(["performanceFeeGovernance", strategy.performanceFeeGovernance()])
    table.append(["performanceFeeStrategist", strategy.performanceFeeStrategist()])
    table.append(["withdrawalFee", strategy.withdrawalFee()])
    table.append(
        ["path0", strategy.getTokenSwapPath(registry.pancake.cake, strategy.token0())]
    )
    table.append(
        ["path1", strategy.getTokenSwapPath(registry.pancake.cake, strategy.token1())]
    )

    print(tabulate(table, headers=["param", "value"]))


def deposit_withdraw_single_user_flow(badger, settConfig, user):
    strategy = badger.getStrategy(settConfig["id"])
    want = interface.IERC20(registry.pancake.chefPairs.bnbBtcb)
    snap = SnapshotManager(badger, settConfig["id"])
    sett = badger.getSett(settConfig["id"])
    settKeeper = accounts.at(sett.keeper(), force=True)

    # Deposit
    assert want.balanceOf(user) > 0

    depositAmount = int(want.balanceOf(user) * 0.8)
    assert depositAmount > 0

    want.approve(sett, MaxUint256, {"from": user})
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

    snap.settWithdrawAll({"from": user})


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def single_user_harvest_flow(badger: BadgerSystem, settConfig, user):
    strategy = badger.getStrategy(settConfig["id"])
    want = interface.IERC20(registry.pancake.chefPairs.bnbBtcb)
    snap = SnapshotManager(badger, settConfig["id"])
    sett = badger.getSett(settConfig["id"])
    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)
    randomUser = accounts[6]

    tendable = strategy.isTendable()

    startingBalance = want.balanceOf(user)

    depositAmount = startingBalance // 200
    assert startingBalance >= depositAmount
    assert startingBalance >= 0

    # Deposit
    want.approve(sett, MaxUint256, {"from": user})
    snap.settDeposit(depositAmount, {"from": user})

    assert want.balanceOf(sett) > 0
    print("want.balanceOf(sett)", want.balanceOf(sett))

    # Earn
    snap.settEarn({"from": settKeeper})

    if tendable:
        with brownie.reverts("onlyAuthorizedActors"):
            strategy.tend({"from": randomUser})

    numTends = 48
    timeBetweenTends = days(365) // numTends

    console.print({"numTends": numTends, "timeBetweenTends": timeBetweenTends})

    for i in range(0, numTends):
        console.print("Tend {}".format(i))
        snap.settTend({"from": strategyKeeper})
        chain.sleep(timeBetweenTends)
        chain.mine()

    with brownie.reverts("onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    snap.settHarvest({"from": strategyKeeper})

    # if tendable:
    #     snap.settTend({"from": strategyKeeper})

    # snap.settWithdraw(depositAmount // 2, {"from": user})

    # chain.sleep(days(3))
    # chain.mine()

    # snap.settHarvest({"from": strategyKeeper})
    # snap.settWithdraw(depositAmount // 2 - 1, {"from": user})


def test_main():
    badger = connect_badger()
    user = accounts[0]
    distribute_test_ether(user, Wei("10 ether"))
    distribute_from_whales(user)
    settConfig = {"id": "native.pancakeBnbBtcb"}
    setup_badger(badger, settConfig)
    deposit_withdraw_single_user_flow(badger, settConfig, user)
    single_user_harvest_flow(badger, settConfig, user)
