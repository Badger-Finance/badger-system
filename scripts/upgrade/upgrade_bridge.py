from brownie import BadgerBridgeAdapter
from rich.console import Console

from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from scripts.systems.bridge_system import BridgeSystem, connect_bridge
from scripts.systems.badger_system import BadgerSystem, connect_badger
from config.badger_config import badger_config

console = Console()


def upgrade_bridge(badger: BadgerSystem, bridge: BridgeSystem) -> str:
    """
    Upgrades bridge.
    """
    adapterLogic = BadgerBridgeAdapter.deploy({"from": badger.deployer})
    bridge.deploy_curve_token_wrapper()

    return badger.queue_upgrade(bridge.adapter.address, adapterLogic.address,)


def configure_bridge(badger: BadgerSystem, bridge: BridgeSystem):
    """
    Configures bridge to use curve token wrapper.
    """

    multi = GnosisSafe(badger.devMultisig)
    id = multi.addTx(
        MultisigTxMetadata(description="Set curve token wrapper on adapter",),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setCurveTokenWrapper.encode_input(
                bridge.curveTokenWrapper.address
            ),
        },
    )
    multi.executeTx(id)


def main():
    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger_config.prod_json)
    upgrade_bridge(badger, bridge)
    console.print("[orange]Queued bridge adapter update[/orange]")

    # TODO: Execute bridge update and configure bridge after delay period.
