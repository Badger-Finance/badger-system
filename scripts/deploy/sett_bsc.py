from helpers.token_utils import distribute_test_ether
import brownie
import decouple
import pytest
from brownie import *
from helpers.constants import *
from helpers.proxy_utils import deploy_proxy, deploy_proxy_admin
from helpers.registry import registry
from helpers.sett.SnapshotManager import SnapshotManager
from helpers.time_utils import days
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from tests.conftest import badger_single_sett, settTestConfig
from tests.helpers import distribute_from_whales

console = Console()

configs = {
    "bnbBtcB": {
        "want": registry.pancake.chefPairs.bnbBtcb,
        "token0": registry.tokens.btcb,
        "token1": registry.tokens.bnb,
        "performanceFeeStrategist": 1000,
        "performanceFeeGovernance": 1000,
        "withdrawalFee": 50,
        "wantPid": registry.pancake.chefPids.bnbBtcb,
    },
    "bBadgerBtcb": {
        "want": registry.pancake.chefPairs.bBadgerBtcb,
        "token0": registry.tokens.bBadger,
        "token1": registry.tokens.btcb,
        "performanceFeeStrategist": 1000,
        "performanceFeeGovernance": 1000,
        "withdrawalFee": 50,
        "wantPid": registry.pancake.chefPids.bBadgerBtcb,
    },
    "bDiggBtcb": {
        "want": registry.pancake.chefPairs.bDiggBtcb,
        "token0": registry.tokens.bDigg,
        "token1": registry.tokens.btcb,
        "performanceFeeStrategist": 1000,
        "performanceFeeGovernance": 1000,
        "withdrawalFee": 50,
        "wantPid": registry.pancake.chefPids.bDiggBtcb,
    },
}


class RevertException(Exception):
    def __init__(self, error, tx):
        self.error = error
        self.tx = tx


def setup_badger(badger: BadgerSystem, settConfig):
    if rpc.is_active():
        seeder = accounts.at("0x3131B6964d96DE3Ad36C7Fe82e9bA9CcdBaf6baa", force=True)
    else:
        seeder = accounts.load("badger_proxy_deployer")

    # Test Proxy Admin (owned by deployer)
    # badger.testProxyAdmin = deploy_proxy_admin(seeder)
    # badger.testProxyAdmin.transferOwnership(badger.deployer, {"from": seeder})

    badger.connect_test_proxy_admin(
        "testProxyAdmin", "0x58A3123f350A469eB4fCA01d8F6E857bc1F61b76"
    )

    config = configs["bDiggBtcb"]
    console.print(config)

    controller = Controller.at("0x4f7d83623eeb135eb13dbcea1a87a96945abe9cc")
    # controller.initialize(
    #     seeder,
    #     badger.deployer,
    #     badger.keeper,
    #     badger.deployer,
    #     {"from": seeder}
    # )

    # Vault
    sett = Sett.at("0xa71ebba5f3f24e84be96240264ae5de38b63860d")
    sett.initialize(
        config["want"],
        controller,
        badger.deployer,
        badger.keeper,
        badger.guardian,
        False,
        "",
        "",
        {"from": seeder},
    )

    # Strategy
    strategyLogic = StrategyPancakeLpOptimizer.at(
        "0xd9dBD1C136e0B7aA7b490Eb7A341924C7c80BBE9"
    )
    strategy = StrategyPancakeLpOptimizer.at(
        "0x98dd0cbd5d32ba198a445de0c4f0ae6b5b56261a"
    )

    strategy.initialize(
        seeder,
        seeder,
        controller,
        badger.keeper,
        badger.guardian,
        [config["want"], config["token0"], config["token1"],],
        [
            config["performanceFeeStrategist"],
            config["performanceFeeGovernance"],
            config["withdrawalFee"],
        ],
        config["wantPid"],
        {"from": seeder},
    )

    token0 = config["token0"]
    token1 = config["token1"]
    cake = registry.pancake.cake

    strategy.setTokenSwapPath(cake, token0, [cake, token0], {"from": seeder})
    strategy.setTokenSwapPath(cake, token1, [cake, token1], {"from": seeder})

    want = interface.IERC20(registry.pancake.chefPairs.bnbBtcb)

    # Wiring
    console.print(controller.address, controller.governance())
    assert controller.governance() == seeder
    controller.approveStrategy(want, strategy, {"from": seeder})
    controller.setStrategy(want, strategy, {"from": seeder})

    strategy.setGovernance(badger.deployer, {"from": seeder})
    # controller.setGovernance(badger.deployer, {"from": seeder})

    badger.setStrategy(settConfig["id"], strategy)
    snap = SnapshotManager(badger, settConfig["id"])

    console.print(
        {
            "controller": controller,
            "sett": sett,
            "strategy": strategy,
            "testProxyAdmin": badger.testProxyAdmin,
        }
    )

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


def main():
    badger = connect_badger()
    badger.deployer = "0xDA25ee226E534d868f0Dd8a459536b03fEE9079b"
    badger.guardian = "0x29F7F8896Fb913CF7f9949C623F896a154727919"
    badger.keeper = "0x872213E29C85d7e30F1C8202FC47eD1Ec124BB1D"
    # user = accounts[0]
    # distribute_test_ether(user, Wei("10 ether"))
    # distribute_from_whales(user)
    settConfig = {"id": "native.pancakeBnbBtcb"}
    setup_badger(badger, settConfig)
