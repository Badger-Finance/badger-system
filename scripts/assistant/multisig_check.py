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
    token = badger.token
    multisig = badger.devMultisig
    convert_to_test_mode(multisig)

    toSet = [
        "native.renCrv",
        "native.sbtcCrv",
        "native.tbtcCrv",
        "harvest.renCrv",
    ]

    for key, strategy in badger.sett_system.strategies.items():
        if key not in toSet:
            print ('Skip:', key)
            continue

        print ('Set WF:', key)
        assert strategy.withdrawalFee() == 75
        encoded = strategy.setWithdrawalFee.encode_input(50)

        print('key: ', key)
        print('to: ', strategy)
        print('data: ', encoded)

        exec_direct(
            contract=multisig,
            params={"to": strategy, "data": encoded},
            signer=badger.deployer
        )
        assert strategy.withdrawalFee() == 50

