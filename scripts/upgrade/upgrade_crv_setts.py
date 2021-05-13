from brownie import SettV1, interface
from rich.console import Console

from config.badger_config import badger_config
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.bridge_system import BridgeSystem, connect_bridge

console = Console()


CRV_SETTS_TO_UPGRADE = [
    "native.renCrv",
    "native.sbtcCrv",
    "native.tbtcCrv",
]


def queue_upgrade_crv_sett(badger: BadgerSystem, settID: str) -> str:
    badger.deploy_logic("SettV1", SettV1)
    logic = badger.logic["SettV1"]
    return badger.queue_upgrade_sett(settID, logic)


def whitelist_adapter_crv_sett(
    badger: BadgerSystem, bridge: BridgeSystem, multi: GnosisSafe, settID: str,
):
    sett = badger.sett_system.vaults[settID]
    id = multi.addTx(
        MultisigTxMetadata(
            description="Approve adapter access to sett {}".format(settID)
        ),
        {
            "to": sett.address,
            "data": sett.approveContractAccess.encode_input(bridge.adapter.address),
        },
    )
    multi.executeTx(id)


def main():
    """
    Queues crv sett upgrades to support depositFor() calls.
    Also whitelists bridge adapter for crv setts.
    """
    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger_config.prod_json)
    multi = GnosisSafe(badger.devMultisig)

    for settID in CRV_SETTS_TO_UPGRADE:
        txFilename = queue_upgrade_crv_sett(badger, settID)
        console.print("[orange] queued up timelock tx {} [/orange]".format(txFilename))
        whitelist_adapter_crv_sett(badger, bridge, multi, settID)
