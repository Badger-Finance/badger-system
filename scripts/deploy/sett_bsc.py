from brownie.network.account import Account
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from ape_safe import ApeSafe
from brownie import *
from brownie import StrategyPancakeLpOptimizer
from helpers.constants import *
from helpers.proxy_utils import deploy_proxy, deploy_proxy_admin
from helpers.registry import registry
from helpers.sett.SnapshotManager import SnapshotManager
from helpers.time_utils import days
from helpers.token_utils import distribute_test_ether
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from tests.conftest import badger_single_sett, settTestConfig
from tests.helpers import distribute_from_whales

console = Console()

configs = {
    "native.pancakeBnbBtcb": {
        "want": registry.pancake.chefPairs.bnbBtcb,
        "token0": registry.tokens.btcb,
        "token1": registry.tokens.bnb,
        "performanceFeeStrategist": 1000,
        "performanceFeeGovernance": 1000,
        "withdrawalFee": 50,
        "wantPid": registry.pancake.chefPids.bnbBtcb,
    },
    "native.bBadgerBtcb": {
        "want": registry.pancake.chefPairs.bBadgerBtcb,
        "token0": registry.tokens.bBadger,
        "token1": registry.tokens.btcb,
        "performanceFeeStrategist": 1000,
        "performanceFeeGovernance": 1000,
        "withdrawalFee": 50,
        "wantPid": registry.pancake.chefPids.bBadgerBtcb,
    },
    "native.bDiggBtcb": {
        "want": registry.pancake.chefPairs.bDiggBtcb,
        "token0": registry.tokens.bDigg,
        "token1": registry.tokens.btcb,
        "performanceFeeStrategist": 1000,
        "performanceFeeGovernance": 1000,
        "withdrawalFee": 50,
        "wantPid": registry.pancake.chefPids.bDiggBtcb,
    },
}


def multisig_action(badger: BadgerSystem):
    multi = GnosisSafe(badger.opsMultisig)
    key = "native.bDiggBtcb"

    vault = badger.getSett(key)
    strategy = badger.getStrategy(key)

    multi.execute(
        MultisigTxMetadata(description="Set PoolId"),
        {"to": strategy.address, "data": strategy.setWantPid.encode_input(104)},
    )

    assert strategy.wantPid() == 104


class RevertException(Exception):
    def __init__(self, error, tx):
        self.error = error
        self.tx = tx


def vault_report(badger: BadgerSystem):
    controller = badger.getController("native")

    for key, vault in badger.sett_system.vaults.items():
        strategy = badger.getStrategy(key)
        snap = SnapshotManager(badger, key)

        snap.printPermissions()

        console.print(
            {
                "want": strategy.want(),
                "token0": strategy.token0(),
                "token1": strategy.token1(),
                "path0": strategy.getTokenSwapPath(
                    registry.pancake.cake, strategy.token0()
                ),
                "path1": strategy.getTokenSwapPath(
                    registry.pancake.cake, strategy.token1()
                ),
            }
        )


def test_upgrades(badger: BadgerSystem, seeder: Account):
    controller = badger.getController("native")

    for key, vault in badger.sett_system.vaults.items():
        assert vault.paused() == False

    for key, strategy in badger.sett_system.strategies.items():
        strategy.setGovernance(badger.opsMultisig, {"from": seeder})


def open_vaults(badger: BadgerSystem, seeder: Account):
    controller = badger.getController("native")

    for key, vault in badger.sett_system.vaults.items():
        vault.unpause({"from": seeder})


def set_governance(badger: BadgerSystem):
    if rpc.is_active():
        seeder = accounts.at("0x3131B6964d96DE3Ad36C7Fe82e9bA9CcdBaf6baa", force=True)
    else:
        seeder = accounts.load("badger_proxy_deployer")

    controller = badger.getController("native")

    table = []

    for key, vault in badger.sett_system.vaults.items():
        assert badger.devProxyAdmin.getProxyAdmin(vault) == badger.devProxyAdmin
        if vault.governance() == seeder:
            vault.setGovernance(badger.opsMultisig, {"from": seeder})
        table.append(["vault", key, vault.address, vault.governance()])

    for key, strategy in badger.sett_system.strategies.items():
        assert badger.devProxyAdmin.getProxyAdmin(strategy) == badger.devProxyAdmin
        if strategy.governance() == seeder:
            strategy.setGovernance(badger.opsMultisig, {"from": seeder})
        table.append(["strategy", key, strategy.address, strategy.governance()])

    if controller.governance() == seeder:
        controller.setGovernance(badger.opsMultisig, {"from": seeder})
    table.append(["controller", "native", controller.address, controller.governance()])

    print(tabulate(table, headers=["type", "key", "address", "governance"]))


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

    controller = badger.getController("native")
    console.print(controller)
    controller.initialize(
        seeder, badger.deployer, badger.keeper, badger.deployer, {"from": seeder}
    )

    assert badger.devProxyAdmin.getProxyAdmin(controller) == badger.devProxyAdmin

    # Strategy
    strategyLogic = badger.logic.StrategyPancakeLpOptimizer
    console.print("strategyLogic", strategyLogic)

    for key, vault in badger.sett_system.vaults.items():
        config = configs[key]
        console.print(key, vault, config)

        want = interface.IERC20(config["want"])

        vault.initialize(
            config["want"],
            controller,
            seeder,
            badger.keeper,
            badger.guardian,
            False,
            "",
            "",
            {"from": seeder},
        )

        controller.setVault(want, vault, {"from": seeder})
        # vault.setGovernance(badger.devMultisig, {"from": seeder})

        assert badger.devProxyAdmin.getProxyAdmin(vault) == badger.devProxyAdmin

    for key, strategy in badger.sett_system.strategies.items():
        config = configs[key]
        console.print(key, strategy, config)

        want = interface.IERC20(config["want"])

        assert badger.devProxyAdmin.getProxyAdmin(strategy) == badger.devProxyAdmin

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

        # Wiring
        console.print(controller.address, controller.governance())
        assert controller.governance() == seeder
        controller.approveStrategy(want, strategy, {"from": seeder})
        controller.setStrategy(want, strategy, {"from": seeder})
        strategy.setStrategist(badger.deployer, {"from": seeder})

        # controller.setGovernance(badger.devMultisig, {"from": seeder})

        badger.setStrategy(key, strategy)
        snap = SnapshotManager(badger, key)

        table = []

        table.append(["governance", strategy.governance()])
        table.append(["strategist", strategy.strategist()])
        table.append(["keeper", strategy.keeper()])
        table.append(["guardian", strategy.guardian()])
        table.append(["want", strategy.want()])
        table.append(["token0", strategy.token0()])
        table.append(["token1", strategy.token1()])
        table.append(["wantPid", strategy.wantPid()])
        table.append(["performanceFeeGovernance", strategy.performanceFeeGovernance()])
        table.append(["performanceFeeStrategist", strategy.performanceFeeStrategist()])
        table.append(["withdrawalFee", strategy.withdrawalFee()])
        table.append(
            [
                "path0",
                strategy.getTokenSwapPath(registry.pancake.cake, strategy.token0()),
            ]
        )
        table.append(
            [
                "path1",
                strategy.getTokenSwapPath(registry.pancake.cake, strategy.token1()),
            ]
        )

        print(tabulate(table, headers=["param", "value"]))

    # print(sett.governance())
    # sett.unpause({"from": seeder})

    # strategy.setWithdrawalFee(config["withdrawalFee"], {"from": seeder})
    # strategy.setPerformanceFeeStrategist(
    #     config["performanceFeeStrategist"], {"from": seeder}
    # )
    # strategy.setPerformanceFeeGovernance(
    #     config["performanceFeeGovernance"], {"from": seeder}
    # )


def main():
    badger = connect_badger()
    badger.deployer = "0xDA25ee226E534d868f0Dd8a459536b03fEE9079b"
    badger.guardian = "0x29F7F8896Fb913CF7f9949C623F896a154727919"
    badger.keeper = "0x872213E29C85d7e30F1C8202FC47eD1Ec124BB1D"

    if rpc.is_active():
        seeder = accounts.at("0x3131B6964d96DE3Ad36C7Fe82e9bA9CcdBaf6baa", force=True)
    else:
        seeder = accounts.load("badger_proxy_deployer")

    # test_upgrades(badger, seeder)
    multisig_action(badger)
