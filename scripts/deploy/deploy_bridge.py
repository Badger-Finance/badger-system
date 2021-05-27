from rich.console import Console
from brownie import interface

# from scripts.systems.badger_system import connect_badger
from scripts.systems import (
    swap_system,
    bridge_system,
)
from config.badger_config import bridge_config, badger_config

console = Console()


def main():
    swap = swap_system.connect_swap(badger_config.prod_json)
    bridge = bridge_system.connect_bridge(badger_config.prod_json)
    bridge.add_existing_swap(swap)
    swap.configure_strategies_grant_swapper_role(bridge.adapter.address)

    confirm_deploy(bridge)
    console.print(
        "[green]deployed bridge adapter at {}[/green]".format(bridge.adapter.address)
    )
    console.print(
        "[green]deployed swap router at {}[/green]".format(bridge.swap.router.address)
    )
    bridge_system.print_to_file(bridge, "deploy-bridge.json")
    swap_system.print_to_file(bridge.swap, "deploy-swap.json")


def confirm_deploy(bridge):
    """
    Redundant sanity checks to confirm various deployment addresses
    are what we expect.
    """
    assert bridge.adapter.governance() == bridge_config.governance
    assert bridge.adapter.rewards() == bridge_config.rewards
    assert bridge.adapter.registry() == bridge_config.registry
    assert bridge.adapter.wBTC() == bridge_config.wbtc
    assert bridge.adapter.mintFeeBps() == bridge_config.mintFeeBps
    assert bridge.adapter.burnFeeBps() == bridge_config.burnFeeBps
    assert bridge.adapter.renBTC() == interface.IGatewayRegistry(
        bridge_config.registry
    ).getTokenBySymbol("BTC")
    assert bridge.adapter.router() == bridge.swap.router.address
