import datetime
from enum import Enum
import json
import os
from scripts.systems.uniswap_system import UniswapSystem
import warnings
import requests
import brownie
import pytest
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from helpers.time_utils import days, to_days, to_timestamp, to_utc_date
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.gnosis_safe import convert_to_test_mode, exec_direct, get_first_owner
from helpers.constants import MaxUint256

console = Console()

def main():
    """
    Connect to badger system, and configure multisig for running transactions in local fork without access to accounts
    """

    # Connect badger system from file
    badger = connect_badger("deploy-final.json")

    # Sanity check file addresses
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    multi = GnosisSafe(badger.devMultisig)

    old_validator="0x29F7F8896Fb913CF7f9949C623F896a154727919"
    new_validator="0x626F69162Ea1556A75Dd4443D87D2fe38dd25901"

    id = multi.addTx(
            MultisigTxMetadata(
                description="Revoke old user"
            ),
            {
                "to": badger.badgerTree.address,
                "data": badger.badgerTree.revokeRole.encode_input(ROOT_VALIDATOR_ROLE, old_validator),
            },
        )

    tx = multi.executeTx(id)

    id = multi.addTx(
        MultisigTxMetadata(
            description="Add new user"
        ),
        {
            "to": badger.badgerTree.address,
            "data": badger.badgerTree.grantRole.encode_input(ROOT_VALIDATOR_ROLE, new_validator),
        },
    )

    tx = multi.executeTx(id)

    assert badger.badgerTree.hasRole(ROOT_VALIDATOR_ROLE, old_validator) == False
    assert badger.badgerTree.hasRole(ROOT_VALIDATOR_ROLE, new_validator) == True

    # Multisig wrapper
    multi = GnosisSafe(badger.devMultisig, testMode=True)
