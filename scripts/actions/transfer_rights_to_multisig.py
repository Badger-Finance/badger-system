import json
import os
import warnings

import brownie
import pytest
from brownie import *
from brownie import accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from helpers.time_utils import days
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

console = Console()


def main():
    badger = connect_badger("deploy-final.json")
    admin = badger.devProxyAdmin
    multisig = badger.devMultisig
    contracts = badger.contracts_upgradeable
    deployer = badger.deployer

    deployer = accounts.load("badger_deployer")

    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert multisig == expectedMultisig

    for key, sett in badger.sett_system.vaults.items():
        sett.setGovernance(multisig, {"from": deployer})
        print(
            "Transferred governance of {} Sett at {} to multisig".format(
                key, sett.address
            )
        )

        assert sett.governance() == expectedMultisig

    for key, strategy in badger.sett_system.strategies.items():
        print(key)
        strategy.setGovernance(multisig, {"from": deployer})
        print(
            "Transferred governance of {} Strategy at {} to multisig".format(
                key, strategy.address
            )
        )

        assert strategy.governance() == expectedMultisig

    for key, controller in badger.sett_system.controllers.items():
        controller.setGovernance(multisig, {"from": deployer})
        print(
            "Transferred governance of {} Controller at {} to multisig".format(
                key, controller.address
            )
        )

        assert controller.governance() == expectedMultisig

    # Transfer proxyAdmins to multisig
    admin.transferOwnership(multisig, {"from": deployer})
    assert admin.owner() == expectedMultisig

    print("Transferred ownership of proxy admin t0 ", multisig)
