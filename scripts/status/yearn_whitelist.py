import time
import json
from brownie import *
from rich.console import Console
from assistant.rewards.rewards_utils import calculate_sett_balances
from assistant.subgraph.client import fetch_wallet_balances
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger

console = Console()

early_access = {}


def filter_zero(balances):
    return dict(filter(lambda elem: elem[1] > 0, balances.items()))


def add_addresses(addresses, point):
    for addr in addresses:
        score = early_access.get(addr, 0) + point
        early_access[addr] = early_access.get(addr, 0) + point

    console.log(early_access)


def main():
    badger = connect_badger(
        badger_config.prod_json, load_keeper=False, load_deployer=False
    )
    bBadger = badger.getSett("native.badger")
    wbtcBadgerUni = badger.getSett("native.uniBadgerWbtc")
    wbtcBadgerSlp = badger.getSett("native.sushiBadgerWbtc")
    crvRenwbtc = badger.getSett("native.renCrv")
    crvRenWsBtc = badger.getSett("native.sbtcCrv")
    tbtc_sbtcCrv = badger.getSett("native.tbtcCrv")
    crvRenWbtc_harvest = badger.getSett("harvest.renCrv")
    wbtcWethSLP = badger.getSett("native.sushiWbtcEth")

    wbtcDiggUni = badger.getSett("native.uniDiggWbtc")
    wbtcDiggSlp = badger.getSett("native.sushiDiggWbtc")
    bDigg = badger.getSett("native.digg")

    condition1Blocks = [11425076, 11548798, 11613974, 11679140]
    condition2Blocks = [11731159, 11835137, 11945691, 12056056]
    condition3Blocks = [11425076, 11613974, 11835137, 12056056]
    condition4Blocks = [11731159, 11835137, 11945691, 12056056]
    condition5Blocks = [11880719, 12056056]

    condition1Addresses = []
    for block in condition1Blocks:
        bBadgerAddreses = filter_zero(
            calculate_sett_balances(badger, "native.badger", bBadger, block)
        ).keys()
        wbtcBadgerUniAddresses = filter_zero(
            calculate_sett_balances(
                badger, "native.uniBadgerWbtc", wbtcBadgerUni, block
            )
        ).keys()
        wbtcBadgerSlpAddreses = filter_zero(
            calculate_sett_balances(
                badger, "native.sushiBadgerWbtc", wbtcBadgerSlp, block
            )
        ).keys()
        combinedAddrs = set(
            [*bBadgerAddreses, *wbtcBadgerUniAddresses, *wbtcBadgerSlpAddreses]
        )
        condition1Addresses.append(combinedAddrs)

    add_addresses(set.intersection(*condition1Addresses), 1)

    condition2Addresses = []
    for block in condition2Blocks:
        bBadgerAddreses = filter_zero(
            calculate_sett_balances(badger, "native.badger", bBadger, block)
        ).keys()
        wbtcBadgerUniAddresses = filter_zero(
            calculate_sett_balances(
                badger, "native.uniBadgerWbtc", wbtcBadgerUni, block
            )
        ).keys()
        wbtcBadgerSlpAddreses = filter_zero(
            calculate_sett_balances(
                badger, "native.sushiBadgerWbtc", wbtcBadgerSlp, block
            )
        ).keys()
        combinedAddrs = set(
            [*bBadgerAddreses, *wbtcBadgerUniAddresses, *wbtcBadgerSlpAddreses]
        )
        condition2Addresses.append(combinedAddrs)

    add_addresses(set.intersection(*condition2Addresses), 1)

    condition3Addresses = []
    for block in condition3Blocks:
        crvRenwbtcAddresses = filter_zero(
            calculate_sett_balances(badger, "native.renCrv", crvRenwbtc, block)
        ).keys()
        crvRenWsBtcAddresses = filter_zero(
            calculate_sett_balances(badger, "native.sbtcCrv", crvRenWsBtc, block)
        ).keys()
        tbtc_sbtcAddresses = filter_zero(
            calculate_sett_balances(badger, "native.tbtcCrv", tbtc_sbtcCrv, block)
        ).keys()
        harvestRenBtcAddresses = filter_zero(
            calculate_sett_balances(badger, "harvest.renCrv", crvRenWbtc_harvest, block)
        ).keys()
        wbtcWethSLPAddresses = filter_zero(
            calculate_sett_balances(badger, "native.sushiWbtcEth", wbtcWethSLP, block)
        ).keys()
        combinedAddrs = set(
            [
                *crvRenwbtcAddresses,
                *crvRenWsBtcAddresses,
                *tbtc_sbtcAddresses,
                *harvestRenBtcAddresses,
                *wbtcWethSLPAddresses,
            ]
        )
        condition3Addresses.append(combinedAddrs)

    add_addresses(set.intersection(*condition3Addresses), 1)

    condition4Addresses = []
    for block in condition4Blocks:
        uniDiggAddrs = filter_zero(
            calculate_sett_balances(badger, "native.uniDiggWbtc", wbtcDiggUni, block)
        ).keys()
        sushiDiggAddrs = filter_zero(
            calculate_sett_balances(badger, "native.sushiDiggWbtc", wbtcDiggSlp, block)
        ).keys()
        bDiggAddrs = filter_zero(
            calculate_sett_balances(badger, "native.digg", bDigg, block)
        ).keys()
        combinedAddrs = set([*uniDiggAddrs, *sushiDiggAddrs, *bDiggAddrs])
        condition4Addresses.append(combinedAddrs)

    add_addresses(set.intersection(*condition4Addresses), 1)

    addrs = []
    uniDiggBalances_old = filter_zero(
        calculate_sett_balances(
            badger, "native.uniDiggWbtc", wbtcDiggUni, condition5Blocks[0]
        )
    )
    uniDiggBalances_new = filter_zero(
        calculate_sett_balances(
            badger, "native.uniDiggWbtc", wbtcDiggUni, condition5Blocks[1]
        )
    )
    for addr, bal in uniDiggBalances_new.items():
        old_bal = uniDiggBalances_old.get(addr, 0)
        if bal > old_bal:
            addrs.append(addr)

    sushiDiggBalances_old = filter_zero(
        calculate_sett_balances(
            badger, "native.sushiDiggWbtc", wbtcDiggSlp, condition5Blocks[0]
        )
    )
    sushiDiggBalances_new = filter_zero(
        calculate_sett_balances(
            badger, "native.sushiDiggWbtc", wbtcDiggSlp, condition5Blocks[1]
        )
    )
    for addr, bal in sushiDiggBalances_new.items():
        old_bal = sushiDiggBalances_old.get(addr, 0)
        if bal > old_bal:
            addrs.append(addr)

    bDiggBalances_old = filter_zero(
        calculate_sett_balances(badger, "native.digg", bDigg, condition5Blocks[0])
    )
    bDiggBalances_new = filter_zero(
        calculate_sett_balances(badger, "native.digg", bDigg, condition5Blocks[1])
    )
    for addr, bal in bDiggBalances_new.items():
        old_bal = bDiggBalances_old.get(addr, 0)
        if bal > old_bal:
            addrs.append(addr)

    add_addresses(set(addrs), 6)
    with open("yearn-whitelist.json", "w") as fp:
        json.dump(early_access, fp, indent=2)
