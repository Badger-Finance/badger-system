from helpers.rewards.LoggerUnlockSchedule import LoggerUnlockSchedule
from scripts.actions.helpers.RewardsSchedule import RewardsSchedule, asset_to_address
from scripts.systems.badger_system import BadgerSystem
from brownie import *
from helpers.utils import shares_to_fragments, to_digg_shares
from helpers.console_utils import console
import datetime
from helpers.time_utils import days, to_timestamp


""" 
Sett              Badger            GDigg
----------------  ------------      -------------
Badger UNI      : 4200.97 (half)       0
Badger Sushi    : 4200.97 (half)       0
Badger Native   : 2100.49 (half)       0
Sushi wbtcEth   : 2346.70              0
Crv RenBTC      : 2346.70              0
Crv SBTC        : 1173.35              0
Crv TBTC        : 1173.35              0
Harvest RenBTC  : 0.00                 0

Digg UNI        : 0                 9.990 (half)
Digg Sushi      : 0                 9.990 (half)
Digg Native     : 0                 4.990 (half)
Yearn WBTC      : 4693.39              0

Crv hBTC        : 3600.00              0
Crv pBTC        : 3600.00              0
Crv oBTC        : 3600.00              0
Crv bBTC        : 3600.00              0
Crv Tricrypto   : 3600.00              0
Cvx Helper      : 360.00               0
CvxCrv Helper   : 360.00               0

"""

weekly_schedule = {
    "native.uniBadgerWbtc": {
        "badger": Wei("4200.97 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("4200.97 ether"),
        "digg": to_digg_shares(0),
    },
    "native.badger": {
        "badger": Wei("2100.49 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiWbtcEth": {
        "badger": Wei("2346.70 ether"),
        "digg": to_digg_shares(0),
    },
    "native.renCrv": {
        "badger": Wei("2346.70 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sbtcCrv": {
        "badger": Wei("1173.35 ether"),
        "digg": to_digg_shares(0),
    },
    "native.tbtcCrv": {
        "badger": Wei("1173.35 ether"),
        "digg": to_digg_shares(0),
    },
    "harvest.renCrv": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(0),
    },
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(9.990),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(9.990),
    },
    "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(4.990)},
    "yearn.wbtc": {"badger": Wei("4693.39 ether"), "digg": to_digg_shares(0)},
    "native.hbtcCrv": {"badger": Wei("3600.00 ether"), "digg": to_digg_shares(0)},
    "native.pbtcCrv": {"badger": Wei("3600.00 ether"), "digg": to_digg_shares(0)},
    "native.obtcCrv": {"badger": Wei("3600.00 ether"), "digg": to_digg_shares(0)},
    "native.bbtcCrv": {"badger": Wei("3600.00 ether"), "digg": to_digg_shares(0)},
    "native.tricrypto": {"badger": Wei("3600.00 ether"), "digg": to_digg_shares(0)},
    "native.cvxCrv": {"badger": Wei("360.00 ether"), "digg": to_digg_shares(0)},
    "native.cvx": {"badger": Wei("360.00 ether"), "digg": to_digg_shares(0)},
}

class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)

def build_weekly_schedules(badger: BadgerSystem, start, duration):
    end = start + duration
    schedules = []
    for key, value in weekly_schedule.items():
        sett = badger.getSett(key)

        for asset, amount in value.items():
            if amount == 0:
                continue
            schedules.append(
                LoggerUnlockSchedule([sett.address, asset_to_address(asset), amount, start, end, duration])
            )
    return schedules

def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 7, 7, 12, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
