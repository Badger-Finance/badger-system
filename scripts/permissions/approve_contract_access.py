from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from ape_safe import ApeSafe
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console

contracts_to_approve = ["0x4459A591c61CABd905EAb8486Bf628432b15C8b1"]

destination_setts = [
    "native.renCrv",
    "native.sbtcCrv",
    "native.tbtcCrv",
    "harvest.renCrv",
    "native.hbtcCrv",
    "native.pbtcCrv",
    "native.obtcCrv",
    "native.bbtcCrv",
    "native.tricrypto",
]


def main():
    badger = connect_badger()
    safe = ApeSafe(badger.devMultisig.address)
    helper = ApeSafeHelper(badger, safe)

    for address in contracts_to_approve:
        for dest_key in destination_setts:
            destination = helper.contract_from_abi(
                badger.getSett(dest_key).address, "SettV3", SettV3.abi
            )
            console.print(
                f"Approve [green]{address}[/green] on Sett [yellow]{dest_key} ({destination.address})"
            )
            destination.approveContractAccess(address)

    helper.publish()
