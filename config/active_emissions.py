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
Badger UNI      : 4916.74 (half)       0
Badger Sushi    : 4916.74 (half)       0
Badger Native   : 2458.37 (half)       0
Sushi wbtcEth   : 2746.53              0
Crv RenBTC      : 2746.53              0
Crv SBTC        : 1373.27              0
Crv TBTC        : 1373.27              0
Harvest RenBTC  : 0.00                 0

Digg UNI        : 0                 11.688 (half)
Digg Sushi      : 0                 11.688 (half)
Digg Native     : 0                 5.844 (half)
Yearn WBTC      : 5493.06             0
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("4916.74 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("4916.74 ether"),
        "digg": to_digg_shares(0),
    },
    "native.badger": {"badger": Wei("2458.37 ether"), "digg": to_digg_shares(0),},
    "native.sushiWbtcEth": {
        "badger": Wei("2746.53 ether"),
        "digg": to_digg_shares(0),
    },
    "native.renCrv": {"badger": Wei("2746.53 ether"), "digg": to_digg_shares(0),},
    "native.sbtcCrv": {"badger": Wei("1373.27 ether"), "digg": to_digg_shares(0),},
    "native.tbtcCrv": {"badger": Wei("1373.27 ether"), "digg": to_digg_shares(0),},
    "harvest.renCrv": {"badger": Wei("0 ether"), "digg": to_digg_shares(0),},
    "native.uniDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(11.688),},
    "native.sushiDiggWbtc": {"badger": Wei("0 ether"), "digg": to_digg_shares(11.688),},
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(5.844)},
    "yearn.wbtc": {"badger": Wei("5493.06 ether"), "digg": to_digg_shares(0)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 6, 3, 13, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
