from helpers.rewards.LoggerUnlockSchedule import LoggerUnlockSchedule
from scripts.actions.helpers.RewardsSchedule import RewardsSchedule, asset_to_address
from scripts.systems.badger_system import BadgerSystem
from brownie import *
from helpers.utils import shares_to_fragments, to_digg_shares
from helpers.console_utils import console
import datetime
from helpers.time_utils import days, to_timestamp

weekly_schedule = {
    # CRV LP
    "native.renCrv": {
        "badger": Wei("3790 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sbtcCrv": {
        "badger": Wei("1895 ether"),
        "digg": to_digg_shares(0),
    },
    "native.tbtcCrv": {
        "badger": Wei("1895 ether"),
        "digg": to_digg_shares(0),
    },
    "native.hbtcCrv": {"badger": Wei("3790 ether"), "digg": to_digg_shares(0)},
    "native.bbtcCrv": {"badger": Wei("3790 ether"), "digg": to_digg_shares(0)},
    "native.obtcCrv": {"badger": Wei("1895 ether"), "digg": to_digg_shares(0)},
    "native.pbtcCrv": {"badger": Wei("1895 ether"), "digg": to_digg_shares(0)},
    "native.tricrypto2": {"badger": Wei("3790 ether"), "digg": to_digg_shares(0)},
    # Sushi LP
    "native.sushiWbtcEth": {
        "badger": Wei("2300 ether"),
        "digg": to_digg_shares(0),
    },
    "experimental.sushiIBbtcWbtc": {
        "badger": Wei("4600 ether"),
        "digg": to_digg_shares(0),
    },
    # Yearn Partner
    "yearn.wbtc": {"badger": Wei("2300 ether"), "digg": to_digg_shares(0)},
    # Convex Helper
    "native.cvx": {"badger": Wei("336 ether"), "digg": to_digg_shares(0)},
    "native.cvxCrv": {"badger": Wei("336 ether"), "digg": to_digg_shares(0)},
    # Native Setts
    "native.badger": {
        "badger": Wei("2300 ether") // 2,
        "digg": to_digg_shares(0),
    },
    "native.uniBadgerWbtc": {
        "badger": Wei("4600 ether") // 2,
        "digg": to_digg_shares(0),
    },
    "native.sushiBadgerWbtc": {
        "badger": Wei("4600 ether") // 2,
        "digg": to_digg_shares(0),
    },
    # Digg Setts
    #  "native.digg": {"badger": Wei("0 ether"), "digg": to_digg_shares(3.43) // 2},
    "native.uniDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(0),
    },
    "native.sushiDiggWbtc": {
        "badger": Wei("0 ether"),
        "digg": to_digg_shares(30.30) // 2,
    },
}


class Emissions:
    def __init__(self, active_emissions):
        self.active = active_emissions


emissions = Emissions(active_emissions=weekly_schedule)


def get_total_weekly_emissions():
    totals = {}
    for key, value in weekly_schedule.items():
        for asset, amount in value.items():
            if not asset in totals:
                totals[asset] = 0
            totals[asset] += amount

    return totals


def build_weekly_schedules(badger: BadgerSystem, start, duration):
    end = start + duration
    schedules = []
    for key, value in weekly_schedule.items():
        sett = badger.getSett(key)

        for asset, amount in value.items():
            if amount == 0:
                continue
            schedules.append(
                LoggerUnlockSchedule(
                    [
                        sett.address,
                        asset_to_address(asset),
                        amount,
                        start,
                        end,
                        duration,
                    ]
                )
            )
    return schedules


def get_active_rewards_schedule(badger: BadgerSystem):
    rest = RewardsSchedule(badger)
    rest.setStart(to_timestamp(datetime.datetime(2021, 8, 12, 1, 00)))
    rest.setDuration(days(7))

    # TODO: Set to read from config emissions. Emit auto-compounding events & on-chain readable data in Unified Rewards Logger.

    rest.setAmounts(emissions.active)
    rest.setTotals(emissions.active)
    return rest
