from helpers.time_utils import days
import json
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.registry import registry
from helpers.registry.artifacts import artifacts
from collections import namedtuple
from config.badger_config import badger_config, digg_config, sett_config
from scripts.systems.badger_system import connect_badger
from scripts.systems.constants import SettType
from helpers.token_utils import distribute_test_ether, distribute_from_whales
from rich.console import Console
from helpers.proxy_utils import deploy_proxy
from helpers.utils import approx
from decimal import Decimal

console = Console()


def main():
    # Assign accounts
    with open(digg_config.prod_json) as f:
        badger_deploy = json.load(f)
        deployer = accounts.at(badger_deploy["deployer"], force=True)
        guardian = accounts.at(badger_deploy["guardian"], force=True)
        keeper = accounts.at(badger_deploy["keeper"], force=True)
        governance = accounts.at(badger_deploy["timelock"], force=True)

    strategist = accounts[3]
    user1 = accounts[4]
    user2 = accounts[5]
    user3 = accounts[6]

    namedAccounts = {
        "deployer": deployer,
        "guardian": guardian,
        "keeper": keeper,
        "governance": governance,
        "strategist": strategist,
        "user1": user1,
        "user2": user2,
        "user3": user3,
    }

    # Setup Badger system
    badger = connect_badger(badger_config.prod_json)
    distribute_test_ether(deployer, Wei("20 ether"))

    # Key of Sett to migrate (ONLY UNCOMMENT THE ONE TO TEST):

    settKey = "native.renCrv"
    # settKey = "native.sbtcCrv"
    # settKey = "native.tbtcCrv"

    # Connect to prod controller and vault
    vault = badger.sett_system.vaults[settKey]
    print("Vault for " + settKey + " fetched with address " + vault.address)

    controller = interface.IController(vault.controller())
    print("Controller for " + settKey + " fetched with address " + controller.address)

    # Deploy and initialize the strategy
    if settKey == "native.renCrv":
        params = sett_config.native.convexRenCrv.params
        want = sett_config.native.convexRenCrv.params.want
        # Transfer assets to users
        distribute_from_whales(user1, 1, "renCrv")
    if settKey == "native.sbtcCrv":
        params = sett_config.native.convexSbtcCrv.params
        want = sett_config.native.convexSbtcCrv.params.want
        # Transfer assets to users
        distribute_from_whales(user1, 1, "sbtcCrv")
    if settKey == "native.tbtcCrv":
        params = sett_config.native.convexTbtcCrv.params
        want = sett_config.native.convexTbtcCrv.params.want
        # Transfer assets to users
        distribute_from_whales(user1, 1, "tbtcCrv")

    contract = StrategyConvexStakingOptimizer.deploy({"from": deployer})
    strategy = deploy_proxy(
        "StrategyConvexStakingOptimizer",
        StrategyConvexStakingOptimizer.abi,
        contract.address,
        web3.toChecksumAddress(badger.devProxyAdmin.address),
        contract.initialize.encode_input(
            governance.address,
            strategist.address,
            controller.address,
            keeper.address,
            guardian.address,
            [
                params.want,
                badger.badgerTree.address,
            ],
            params.pid,
            [
                params.performanceFeeGovernance,
                params.performanceFeeStrategist,
                params.withdrawalFee,
            ],
        ),
        deployer,
    )

    # Finish setup

    return namedtuple("setup", "badger controller vault strategy namedAccounts")(
        badger, controller, vault, strategy, namedAccounts
    )
