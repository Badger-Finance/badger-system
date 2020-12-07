import os
import json
from scripts.systems.badger_system import connect_badger
import warnings
from tabulate import tabulate
from brownie import interface, accounts, rpc
from dotmap import DotMap
from helpers.registry import registry

from helpers.time_utils import daysToSeconds
from brownie import *
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from config.badger_config import badger_config
from scripts.systems.badger_system import BadgerSystem
from rich.console import Console
import pytest
import brownie

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
        # sett.setGovernance(multisig, {"from": deployer})
        # print(
        #     "Transferred governance of {} Sett at {} to multisig".format(
        #         key, sett.address
        #     )
        # )
        
        assert sett.governance() == expectedMultisig

    for key, strategy in badger.sett_system.strategies.items():
        # if key != "native.badger" and key != "native.renCrv" and key != "native.sbtcCrv":
        #     print(key)
        #     strategy.setGovernance(multisig, {"from": deployer})
        #     print(
        #         "Transferred governance of {} Strategy at {} to multisig".format(
        #             key, strategy.address
        #         )
        #     )

        assert strategy.governance() == expectedMultisig

    for key, controller in badger.sett_system.controllers.items():
        # controller.setGovernance(multisig, {"from": deployer})
        # print(
        #     "Transferred governance of {} Controller at {} to multisig".format(
        #         key, controller.address
        #     )
        # )

        assert controller.governance() == expectedMultisig


    # Transfer proxyAdmins to multisig
    # admin.transferOwnership(multisig, {"from": deployer})
    assert admin.owner() == expectedMultisig
    print("Transferred ownership of proxy admin t0 ", multisig)

