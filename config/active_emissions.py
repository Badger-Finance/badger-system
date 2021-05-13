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
Badger UNI      : 6845.35 (half)       0.464
Badger Sushi    : 6845.35 (half)       0.464
Badger Native   : 3422.67 (half)       0.232
Sushi wbtcEth   : 5353.41              0.363
Crv RenBTC      : 5353.41              0.363
Crv SBTC        : 5353.41              0.363
Crv TBTC        : 5353.41              0.363
Harvest RenBTC  : 5353.41              0.363

Digg UNI        : 0                 15.083 (half)
Digg Sushi      : 0                 15.083 (half)
Digg Native     : 0                 7.542 (half)
Yearn WBTC      : 23339.12             0
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("6845.35 ether"),
        "digg": to_digg_shares(0.464),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("6845.35 ether"),
        "digg": to_digg_shares(0.464),
    },
    "native.badger": {"badger": Wei("3422.67 ether"), "digg": to_digg_shares(0.232),},
    "native.sushiWbtcEth": {
        "badger": Wei("5353.41 ether"),
        "digg": to_digg_shares(0.363),
    },
    "native.renCrv": {"badger": Wei("5353.41 ether"), "digg": to_digg_shares(0.363),},
    "native.sbtcCrv": {"badger": Wei("5353.41 ether"), "digg": to_digg_shares(0.363),},
    "native.tbtcCrv": {"badger": Wei("5353.41 ether"), "digg": to_digg_shares(0.363),},
    "harvest.renCrv": {"badger": Wei("5353.41 ether"), "digg": to_digg_shares(0.363),},
    "native.uniDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(15.083),},
    "native.sushiDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(15.083),},
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(7.542)},
    "yearn.wbtc": {"badger": Wei("23339.12 ether"), "digg": to_digg_shares(0)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 5, 6, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
