from scripts.systems.badger_system import BadgerSystem, connect_badger
from brownie import *
from helpers.registry import registry


def snap_strategy_balance(badger: BadgerSystem, key, manager):
    digg = badger.digg

    strategy = badger.getStrategy(key)
    sett = badger.getSett(key)

    want = interface.IERC20(strategy.want())
    wbtc = interface.IERC20(registry.tokens.wbtc)

    state = {
        "manager (badger)": badger.token.balanceOf(manager),
        "manager (digg)": digg.token.balanceOf(manager),
        "manager (want)": want.balanceOf(manager),
        "manager (wbtc)": wbtc.balanceOf(manager),
        "balanceOfPool": strategy.balanceOfPool(),
        "balanceOfWant": strategy.balanceOfWant(),
        "balanceOf": strategy.balanceOf(),
        "pricePerFullShare": sett.getPricePerFullShare(),
    }
    return state


def diff_numbers_by_key(a, b):
    diff = {}
    for key, a_value in a.items():
        b_value = b[key]
        diff[key] = b_value - a_value
    return diff
