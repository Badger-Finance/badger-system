from brownie import SettV1, interface
from rich.console import Console

from helpers.sett.SnapshotManager import SnapshotManager
from config.badger_config import badger_config
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.bridge_system import BridgeSystem, connect_bridge

console = Console()


TX_HASHES = [
    "0x1f16dbc7d429e8026d143457756f248dbf2617c2211087edb5aa667caeb1a6e4.json",
    "0x032a28df32bd4797067b0e7595ae138fc7a274144d6f319d5e46342f693148ee.json",
]

setts = ["native.sushiBadgerWbtc", "native.sushiDiggWbtc"]


def main():
    """
    Load queued tx from file for execution on timelock
    """
    badger = connect_badger(badger_config.prod_json)
    multi = GnosisSafe(badger.devMultisig)

    for txFilename in TX_HASHES:
        badger.governance_execute_transaction(txFilename, remove_file_on_success=False)

    for settID in setts:
        strategy = badger.getStrategy(settID)
        snap = SnapshotManager(badger, settID)
        snap.settHarvestViaManager(strategy, {"from": badger.keeper})
