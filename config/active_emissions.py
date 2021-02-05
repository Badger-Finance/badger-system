from brownie import *
from helpers.utils import shares_to_fragments, to_digg_shares

schedules = {
    "native.uniBadgerWbtc": {
        "badger": Wei("23338.61 ether"),
        "digg": to_digg_shares(6.42),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("23338.61 ether"),
        "digg": to_digg_shares(6.42),
    },
    "native.badger": {"badger": Wei("11669.31 ether"), "digg": to_digg_shares(3.21),},
    "native.sushiWbtcEth": {
        "badger": Wei("18251.99 ether"),
        "digg": to_digg_shares(5.02),
    },
    "native.renCrv": {"badger": Wei("18251.99 ether"), "digg": to_digg_shares(5.02),},
    "native.sbtcCrv": {"badger": Wei("18251.99 ether"), "digg": to_digg_shares(5.02),},
    "native.tbtcCrv": {"badger": Wei("18251.99 ether"), "digg": to_digg_shares(5.02),},
    "harvest.renCrv": {"badger": Wei("18251.99 ether"), "digg": to_digg_shares(5.02),},
    "native.uniDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(39.00),},
    "native.sushiDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(39.00),},
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(19.50)},
}

# Convert DIGG to current fragments scale for transfers
# TODO: Update rewards manager to be able to transfer from share value

active_emissions = schedules
for source, assets in schedules.items():
    for asset, value in assets.items():
        if asset == "digg":
            active_emissions[source][asset] = shares_to_fragments(
                active_emissions[source][asset]
            )


def get_daily_amount(key, asset):
    return active_emissions[key][asset] // 7


def get_half_daily_amount(key, asset):
    return active_emissions[key][asset] // 14

