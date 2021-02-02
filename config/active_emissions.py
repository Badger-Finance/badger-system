from brownie import *
from helpers.utils import shares_to_fragments, to_digg_shares

active_emissions = {
    "native.uniBadgerWbtc": {
        "badger": Wei("25897 ether"),
        "digg": shares_to_fragments(to_digg_shares(17.86)),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("25897 ether"),
        "digg": shares_to_fragments(to_digg_shares(17.86)),
    },
    "native.badger": {
        "badger": Wei("12949 ether"),
        "digg": shares_to_fragments(to_digg_shares(8.93)),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("20253 ether"),
        "digg": shares_to_fragments(to_digg_shares(13.97)),
    },
    "native.renCrv": {
        "badger": Wei("20253 ether"),
        "digg": shares_to_fragments(to_digg_shares(13.97)),
    },
    "native.sbtcCrv": {
        "badger": Wei("20253 ether"),
        "digg": shares_to_fragments(to_digg_shares(13.97)),
    },
    "native.tbtcCrv": {
        "badger": Wei("20253 ether"),
        "digg": shares_to_fragments(to_digg_shares(13.97)),
    },
    "harvest.renCrv": {
        "badger": Wei("20253 ether"),
        "digg": shares_to_fragments(to_digg_shares(13.97)),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": shares_to_fragments(to_digg_shares(31.16)),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": shares_to_fragments(to_digg_shares(31.16)),
    },
    "native.digg": {
        "badger": Wei("0 ether"),
        "digg": shares_to_fragments(to_digg_shares(15.58)),
    },
}

def get_daily_amount(key, asset):
    return active_emissions[key][asset] // 7


def get_half_daily_amount(key, asset):
    return active_emissions[key][asset] // 14

