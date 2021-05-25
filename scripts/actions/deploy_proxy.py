from dotmap import DotMap
from helpers.proxy_utils import deploy_proxy
from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from helpers.time_utils import days, hours
import os
import json
from scripts.systems.badger_system import connect_badger
import warnings
from tabulate import tabulate
from brownie import *
from helpers.registry import registry
from rich.console import Console
from config.badger_config import badger_config
from helpers.gas_utils import gas_strategies

console = Console()


def main():
    badger = connect_badger(badger_config.prod_json)
    deployer = badger.deployer
    # distribute_from_whales(deployer)

    # Deploy Honeypot
    artifact = BadgerRewardsManager
    logic = BadgerRewardsManager.at(badger.logic.BadgerRewardsManager)
    console.print("Logic Contract", logic)

    contract = deploy_proxy(
        "BadgerRewardsManager",
        artifact.abi,
        logic.address,
        badger.devProxyAdmin.address,
        logic.initialize.encode_input(
            badger.deployer,
            badger.keeper,
            badger.keeper,
            badger.guardian,
            badger.devMultisig,
        ),
        deployer,
    )

    strat_keys = [
        "native.badger",
        "native.uniBadgerWbtc",
        "native.sushiBadgerWbtc",
        "native.digg",
        "native.uniDiggWbtc",
        "native.sushiDiggWbtc",
    ]

    for key in strat_keys:
        strategy = badger.getStrategy(key)
        print(key, strategy)
        contract.approveStrategy(
            strategy, {"from": badger.deployer, "gas_strategy": gas_strategies.fast}
        )
