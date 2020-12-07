from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from helpers.time_utils import daysToSeconds
import os
import json
from scripts.systems.badger_system import connect_badger
import warnings
from tabulate import tabulate
from brownie import *
from helpers.registry import registry
from rich.console import Console
console = Console()

def main():
    test = True
    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName)

    multisig = badger.devMultisig

    deployer = badger.deployer
    multisig = badger.devMultisig
    admin = badger.devProxyAdmin
    contract = badger.badgerHunt
    
    newLogic = BadgerHunt.deploy({"from": deployer, "allow_revert": True})
    encoded = admin.upgrade.encode_input(contract, newLogic)

    convert_to_test_mode(multisig)
    exec_direct(multisig, {
        'to': admin.address,
        "data": encoded
    }, deployer)

    print("New Logic")
    print(newLogic.address)

    print("Upgrade")
    encoded = admin.upgrade.encode_input(contract, newLogic)
    print(encoded)

    print("Set Param")
    param = badger.badgerHunt.setGracePeriod.encode_input(daysToSeconds(5))
    print(param)

    exec_direct(multisig, {
        'to': contract.address,
        "data": param
    }, deployer)
    print(daysToSeconds(5))
    assert contract.gracePeriod() == daysToSeconds(5)