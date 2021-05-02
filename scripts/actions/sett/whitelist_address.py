from ape_safe import ApeSafe
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import (
    ApeSafeHelper,
    GnosisSafe,
    MultisigTxMetadata,
    convert_to_test_mode,
    exec_direct,
    get_first_owner,
)
from helpers.registry import registry
from helpers.time_utils import days, to_days, to_timestamp, to_utc_date
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

console = Console()

contracts_to_approve = ["0x3e2Ba76558350c7DF7077379f7D429707623c9D2"]


def main():
    # Connect badger system from file
    badger = connect_badger()

    # Sanity check file addresses
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    safe = ApeSafe(badger.devMultisig.address)
    helper = ApeSafeHelper(badger, safe)

    sett = helper.getSett("native.renCrv")

    for contract in contracts_to_approve:
        sett.approveContractAccess(contract)

    assert sett.approved(contract) == True

    helper.publish()
