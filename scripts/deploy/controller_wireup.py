import time

from brownie import (
    accounts,
    network,
    Controller,
    StrategyConvexStakingOptimizer,
    SettV4,
)

import click
from rich.console import Console

from helpers.constants import AddressZero

console = Console()

sleep_between_tx = 1


def main():
    # dev must be the controller's governance (get from keystore)
    dev = connect_account()

    # NOTE: Add the strategies, vaults and their corresponding wants
    # to the arrays below. It is very important that indexes are the
    # same for corresponding contracts. Example: to wire SettA, the
    # address of strategyA, vaultA and wantA must all be position at
    # the same index within their respective arrays.

    # Strategies to wire up
    strategies = [
        "0xe66dB6Eb807e6DAE8BD48793E9ad0140a2DEE22A",
        "0x2f278515425c8eE754300e158116930B8EcCBBE1",
        "0x9e0742EE7BECde52A5494310f09aad639AA4790B",
        "0x7354D5119bD42a77E7162c8Afa8A1D18d5Da9cF8",
        "0x3f98F3a21B125414e4740316bd6Ef14718764a22",
        "0x50Dd8A61Bdd11Cf5539DAA83Bc8E0F581eD8110a",
        "0xf92660E0fdAfE945aa13616428c9fB4BE19f4d34",
        "0xf3202Aa2783F3DEE24a35853C6471db065B05D37",
        "0xf6D442Aead5960b283281A794B3e7d3605601247",
        "0xc67129cf19BB00d60CC5CF62398fcA3A4Dc02a14",
    ]
    # Vaults to wire up
    vaults = [
        "0xD3eC271d07f2f9a4eB5dfD314f84f8a94ba96145",
        "0x8D7A5Bacbc763b8bA7c2BB983089b01bBF3C9408",
        "0xe71246810751dfaf8430dcd838a1e58A904a2725",
        "0x8E8Fd0dD9F8C69E621054538Fb106Ae77B0847DD",
        "0xdD954ff59A99352aCF16AAd0801350a0742359E3",
        "0x0eC330A6f4e93204B9AA62a4e7A0C78D7849821E",
        "0x68e8efd42A22BF4B53ecE7162d9aCbA2Ad2f9991",
        "0x29001E42899308A61d981c5f5780e4E4D727a0BB",
        "0x4d9ed3cb6a84aff2580b411C9999D2F215311670",
        "0x7874C31fa126d522BE96Ebf6E054Ee4413Ca23a9",
    ]

    controllerAddr = "0xe505F7C2FFcce7Ae4b076456BC02A70D8fe8d4d2"
    assert controllerAddr != AddressZero
    controller = Controller.at(controllerAddr)

    # Wire up strategies
    for strat in strategies:
        vault = SettV4.at(vaults[strategies.index(strat)])
        strategy = StrategyConvexStakingOptimizer.at(strat)

        console.print(f"[yellow]Wiring up {vault.name()}[/yellow]")

        assert vault.token() == strategy.want()

        want = vault.token()

        console.print("Strategy: ", strat)
        console.print("Vault:", vault.address)
        console.print("Want:", want)

        controller.approveStrategy(want, strat, {"from": dev})
        time.sleep(sleep_between_tx)
        assert controller.approvedStrategies(want, strat) == True

        controller.setStrategy(want, strat, {"from": dev})
        time.sleep(sleep_between_tx)
        assert controller.strategies(want) == strat

        controller.setVault(want, vault.address, {"from": dev})
        time.sleep(sleep_between_tx)
        assert controller.vaults(want) == vault.address
        console.print(f"[green]Wiring up completed![/green]")

def connect_account():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")
    return dev