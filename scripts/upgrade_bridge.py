from brownie import (
    BadgerBridgeAdapter,
    CurveSwapStrategy,
    network,
)
from rich.console import Console

from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from scripts.systems.bridge_system import BridgeSystem, connect_bridge
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.swap_system import connect_swap
from config.badger_config import badger_config
from helpers.registry import registry

console = Console()


def upgrade_swap_strategy(
    badger: BadgerSystem,
    strategy: network.contract.ProjectContract,
    SwapStrategy: network.contract.ContractContainer,
) -> str:
    """
    Upgrades swap strategy.
    """
    logic = SwapStrategy.deploy({"from": badger.deployer})
    return badger.queue_upgrade(
        strategy.address,
        logic.address,
    )


def upgrade_bridge(badger: BadgerSystem, bridge: BridgeSystem) -> str:
    """
    Upgrades bridge.
    """
    # adapterLogic = BadgerBridgeAdapter.deploy({"from": badger.deployer})
    adapterLogic = BadgerBridgeAdapter.at("0x21b5daa9c170ed13ef4046b4b528dbe14c9b763a")
    
    return badger.queue_upgrade(
        bridge.adapter.address,
        adapterLogic.address,
    )


def configure_bridge(badger: BadgerSystem, bridge: BridgeSystem):
    """
    Configures bridge for ibbtc.
    """

    multi = GnosisSafe(badger.devMultisig)

    yearnWbtc = connect_badger("deploy-final.json")
    wbtcAddr = yearnWbtc.sett_system["vaults"]["yearn.wbtc"]

    multi.execute(
        MultisigTxMetadata(description="add defi dollar contract addresses to adapter contract"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setIbbtcContracts.encode_input(registry.defidollar.addresses.ibbtc, registry.defidollar.addresses.badgerPeak, registry.defidollar.addresses.wbtcPeak),
        },
    )

    for pool in registry.defidollar.pools:
        multi.execute(
            MultisigTxMetadata(description="populate vault/poolid dictionary"),
            {
                "to": bridge.adapter.address,
                "data": bridge.adapter.setVaultPoolId.encode_input(pool.sett, pool.id),
            },
        )

    multi.execute(
        MultisigTxMetadata(description="populate vault/poolid dictionary"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setVaultPoolId.encode_input(wbtcAddr, 3),
        },
    )


def main():
    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    swap = connect_swap(badger_config.prod_json)

    upgrade_bridge(badger, bridge)
    console.print("[orange]Queued bridge adapter update[/orange]")

    #upgrade_swap_strategy(badger, swap.strategies.curve, CurveSwapStrategy)
    #console.print("[orange]Queued swap strategy update[/orange]")

    #bridge.deploy_curve_token_wrapper()
    configure_bridge(badger, bridge)
    console.print("[orange]Configured bridge for ibbtc[/orange]")

    # TODO: Execute bridge update and configure bridge after delay period.
