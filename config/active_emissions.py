from scripts.actions.helpers.RewardsSchedule import RewardsSchedule
from scripts.systems.badger_system import BadgerSystem
from brownie import *
from helpers.utils import shares_to_fragments, to_digg_shares
from helpers.console_utils import console
import datetime
from helpers.time_utils import days, to_timestamp


""" 
Sett              Badger            GDigg
----------------  ------------      -------------
Badger UNI      : 15610.58 (half)       3.733
Badger Sushi    : 15610.58 (half)       3.733
Badger Native   : 7805.29 (half)        1.866
Sushi wbtcEth   : 12208.28              2.919
Crv RenBTC      : 12208.28              2.919
Crv SBTC        : 12208.28              2.919
Crv TBTC        : 12208.28              2.919
Harvest RenBTC  : 12208.28              2.919

Digg UNI        : 0                 27.537 (half)
Digg Sushi      : 0                 27.537 (half)
Digg Native     : 0                 13.768 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("15610.58 ether"),
        "digg": to_digg_shares(3.733),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("15610.58 ether"),
        "digg": to_digg_shares(3.733),
    },
    "native.badger": {
        "badger": Wei("7805.29 ether"),
        "digg": to_digg_shares(1.866),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("12208.28 ether"),
        "digg": to_digg_shares(2.919),
    },
    "native.renCrv": {
        "badger": Wei("12208.28 ether"),
        "digg": to_digg_shares(2.919),
    },
    "native.sbtcCrv": {
        "badger": Wei("12208.28 ether"),
        "digg": to_digg_shares(2.919),
    },
    "native.tbtcCrv": {
        "badger": Wei("12208.28 ether"),
        "digg": to_digg_shares(2.919),
    },
    "harvest.renCrv": {
        "badger": Wei("12208.28 ether"),
        "digg": to_digg_shares(2.919),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(27.537),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(27.537),
    },
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(13.768)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 3, 4, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
