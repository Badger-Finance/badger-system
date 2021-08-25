import time

from brownie import (
    accounts,
    network,
    Controller,
)

import click
from rich.console import Console

console = Console()

sleep_between_tx = 1


def main():
    dev = connect_account()

    strategies = [
        "0xDed61Bd8a8c90596D8A6Cf0e678dA04036146963",
        "0xDb0C3118ef1acA6125200139BEaCc5D675F37c9C",
        "0xF8F02D0d41C79a1973f65A440C98acAc7eAA8Dc1",
        "0x809990849D53a5109e0cb9C446137793B9f6f1Eb",
    ]

    vaults = [
        "0xEa8567d84E3e54B32176418B4e0C736b56378961",
        "0x85E1cACAe9a63429394d68Db59E14af74143c61c",
        "0x7B6bfB88904e4B3A6d239d5Ed8adF557B22C10FC",
        "0x6B2d4c4bb50274c5D4986Ff678cC971c0260E967",
    ]

    wants = [
        "0x8F8e95Ff4B4c5E354ccB005c6B0278492D7B5907",
        "0x8096ac61db23291252574d49f036f0f9ed8ab390",
        "0xf8a57c1d3b9629b77b6726a042ca48990a84fb49",
        "0xF6a637525402643B0654a54bEAd2Cb9A83C8B498",
    ]

    controller = Controller.at("0xc00e71719d1494886942d6277daea20494cf0eec")

    # Wire up strategies
    for strat in strategies:
        want = wants[strategies.index(strat)]

        controller.approveStrategy(want, strat, {"from": dev})
        time.sleep(sleep_between_tx)
        assert controller.approvedStrategies(want) == strat

        controller.setStrategy(want, strat, {"from": dev})
        time.sleep(sleep_between_tx)
        assert controller.strategies(want) == strat

    # Wire up vaults
    for vault in vaults:
        want = wants[vaults.index(vault)]

        controller.setVault(want, vault, {"from": dev})
        time.sleep(sleep_between_tx)
        assert controller.vaults(want) == vault


def connect_account():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")
    return dev
