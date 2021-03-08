from brownie import *
import math

from rich.console import Console
from assistant.subgraph.client import (
    fetch_sett_balances,
    fetch_geyser_events,
    fetch_cream_deposits
)
from collections import Counter,OrderedDict
from assistant.rewards.rewards_utils import (
    combine_balances,
    calc_balances_from_geyser_events,
    fetch_sett_price,
    fetch_sett_ppfs
)
console = Console()

APPROVED_CONTRACTS = {}

def convert_balances_to_usd(sett,balances):
    price = fetch_sett_price(sett.token().lower())
    ppfs = fetch_sett_ppfs(sett.token().lower())
    for account,bBalance in balances.items():
        balances[account] = (price * bBalance * ppfs)/1e18
    return balances

def calc_cumulative(l):
    result = [None] * len(l)
    console.log(l)
    cumulative = 0
    for idx,val in enumerate(l):
        cumulative += val
        result[idx] = cumulative
    return result

def get_sett_addresses(setts):
    addresses = []
    for name,balances in setts.items():
        addresses.extend(list(balances.keys()))
    return set(addresses)


def calculate_sett_balances(badger,name,sett,currentBlock):
    settBalances = fetch_sett_balances(sett.address.lower(),currentBlock)
    settUnderlyingToken = interface.ERC20(sett.token())
    geyserBalances = {}
    creamBalances = {}
    # Digg doesn't have a geyser so we have to ignore it 
    if name != "native.digg":
        geyserEvents = fetch_geyser_events(badger.getGeyser(name).address.lower(),currentBlock)
        geyserBalances = calc_balances_from_geyser_events(geyserEvents)

    creamBalances = fetch_cream_deposits("cr{}".format(settUnderlyingToken.symbol()))
    return combine_balances([settBalances,geyserBalances,creamBalances])


def calc_address_balances(address,diggSetts,badgerSetts,nonNativeSetts):
    diggBalance = 0
    badgerBalance = 0
    nonNativeBalance = 0
    for name,balances in diggSetts.items():
        diggBalance += balances.get(address,0)
    for name,balances in badgerSetts.items():
        badgerBalance += balances.get(address,0)
    for name,balances in nonNativeSetts.items():
        nonNativeBalance += balances.get(address,0)

    return(diggBalance,badgerBalance,nonNativeBalance)

def get_balance_data(badger,currentBlock):
    allSetts = badger.sett_system.vaults
    diggSetts = {}
    badgerSetts = {}
    nonNativeSetts = {}
    for name,sett in allSetts.items():
        balances = calculate_sett_balances(badger,name,sett,currentBlock)
        balances = convert_balances_to_usd(sett,balances)
        if name in ["native.uniDiggWbtc","native.sushiDiggWbtc","native.digg"]:
            diggSetts[name] = balances
        elif name in ["native.badger","native.uniBadgerWbtc","native.sushiBadgerWbtc"]:
            badgerSetts[name] = balances
        else:
            nonNativeSetts[name] = balances

    badger_wallet_balances, digg_wallet_balances = fetch_wallet_balances()
    # TODO: Merge the usd value of these with the correct balances

    allAddresses = get_sett_addresses(diggSetts).union(get_sett_addresses(badgerSetts).union(get_sett_addresses(nonNativeSetts)))
    
    stakeRatios = [calc_stake_ratio(addr,diggSetts,badgerSetts,nonNativeSetts) for addr in allAddresses]
    console.log(stakeRatios)
    