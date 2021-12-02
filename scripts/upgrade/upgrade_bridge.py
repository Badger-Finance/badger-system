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
    adapterLogic = BadgerBridgeAdapter.deploy({"from": badger.deployer})

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
        MultisigTxMetadata(description="set new curvetokenwrapper"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setCurveTokenWrapper.encode_input("NEW CURVETOKENWRAPPER ADDRESS HERE"),
        },
    )

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

    multi.execute(
        MultisigTxMetadata(description="approve rencrv vault"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setVaultApproval.encode_input("0x6dEf55d2e18486B9dDfaA075bc4e4EE0B28c1545", True),
        },
    )

    multi.execute(
        MultisigTxMetadata(description="approve sbtccrv vault"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setVaultApproval.encode_input("0xd04c48A53c111300aD41190D63681ed3dAd998eC", True),
        },
    )

    multi.execute(
        MultisigTxMetadata(description="approve tbtccrv vault"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setVaultApproval.encode_input("0xb9D076fDe463dbc9f915E5392F807315Bf940334", True),
        },
    )

    multi.execute(
        MultisigTxMetadata(description="approve yearn vault"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setVaultApproval.encode_input("0x4b92d19c11435614cd49af1b589001b7c08cd4d5", True),
        },
    )

    multi.execute(
        MultisigTxMetadata(description="approve ibbtccrv vault"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setVaultApproval.encode_input("0xaE96fF08771a109dc6650a1BdCa62F2d558E40af", True),
        },
    )


def main():
    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    #swap = connect_swap(badger_config.prod_json)

    #upgrade_bridge(badger, bridge)
    #console.print("[orange]Queued bridge adapter update[/orange]")

    #upgrade_swap_strategy(badger, swap.strategies.curve, CurveSwapStrategy)
    #console.print("[orange]Queued swap strategy update[/orange]")

    #bridge.deploy_curve_token_wrapper()
    configure_bridge(badger, bridge)
    console.print("[orange]Configured bridge[/orange]")

    # TODO: Execute bridge update and configure bridge after delay period.
