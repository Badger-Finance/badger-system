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
Badger UNI      : 8899.75 (half)       0
Badger Sushi    : 8899.75 (half)       0
Badger Native   : 4449.88 (half)        0
Sushi wbtcEth   : 6960.06              0
Crv RenBTC      : 6960.06              0
Crv SBTC        : 6960.06              0
Crv TBTC        : 6960.06              0
Harvest RenBTC  : 6960.06              0

Digg UNI        : 0                 21.155 (half)
Digg Sushi      : 0                 21.155 (half)
Digg Native     : 0                 10.578 (half)
"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("8899.75 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("8899.75 ether"),
        "digg": to_digg_shares(0),
    },
    "native.badger": {
        "badger": Wei("4449.88 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("6960.06 ether"),
        "digg": to_digg_shares(0),
    },
    "native.renCrv": {
        "badger": Wei("6960.06 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sbtcCrv": {
        "badger": Wei("6960.06 ether"),
        "digg": to_digg_shares(0),
    },
    "native.tbtcCrv": {
        "badger": Wei("6960.06 ether"),
        "digg": to_digg_shares(0),
    },
    "harvest.renCrv": {
        "badger": Wei("6960.06 ether"),
        "digg": to_digg_shares(0),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(21.155),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(21.155),
    },
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(10.578)},
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 4, 15, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
