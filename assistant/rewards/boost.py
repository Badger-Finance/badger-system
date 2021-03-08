from brownie import *
from rich.console import Console
from assistant.subgraph.client import (
    fetch_sett_balances, 
    fetch_geyser_events, 
    fetch_cream_bbadger_deposits,
    fetch_wallet_balances
)
from collections import Counter
from assistant.rewards.rewards_utils import (
    combine_balances,
    calc_balances_from_geyser_events,
    fetch_sett_price,
    fetch_sett_ppfs
)
console = Console()

APPROVED_CONTRACTS = {}


def get_sett_addresses(setts):
    addresses = []
    for name,balances in setts.items():
        addresses.extend(list(balances.keys()))

    return set(addresses)
        

def calc_stake_ratio(address,diggSetts,badgerSetts,nonNativeSetts):
    diggBalance = 0
    badgerBalance = 0
    nonNativeBalance = 0
    for name,balances in diggSetts.items():
        diggBalance += balances.get(address,0)
    for name,balances in badgerSetts.items():
        badgerBalance += balances.get(address,0)
    for name,balances in diggSetts.items():
        nonNativeBalance += balances.get(address,0)
    
    if nonNativeBalance == 0:
        return 0
    else:
        return (diggBalance + badgerBalance )/ nonNativeBalance

def get_balance_data(badger,currentBlock):
    allSetts = badger.sett_system.vaults
    console.log(allSetts)
    diggSetts = {}
    badgerSetts = {}
    nonNativeSetts = {}
    for name,sett in allSetts.items():
        balances = calculate_sett_balances(badger,name,sett,currentBlock)
        if name in ["native.uniDiggWbtc","native.sushiDiggWbtc","native.digg"]:
            diggSetts[name] = balances
        elif name in ["native.badger","native.uniBadgerWbtc","native.sushiBadgerWbtc"]:
            badgerSetts[name] = balances
        else:
            nonNativeSetts[name] = balances

    badger_wallet_balances, digg_wallet_balances = fetch_wallet_balances()

    # Include bBadger deposits on CREAM and Badger wallet balances (merge this with native.badger)
    badgerSetts["native.badger"] = dict(
        Counter(fetch_cream_bbadger_deposits()) + Counter(badgerSetts["native.badger"]) + Counter(badger_wallet_balances)
    )
    # Include Digg wallet balances (merge this with native.digg)
    diggSetts["native.digg"] = dict(
        Counter(digg_wallet_balances) + Counter(diggSetts["native.digg"])
    )
    allAddresses = get_sett_addresses(diggSetts).union(get_sett_addresses(badgerSetts).union(get_sett_addresses(nonNativeSetts)))
    
    stakeRatios = [calc_stake_ratio(addr,diggSetts,badgerSetts,nonNativeSetts) for addr in allAddresses]
    console.log(stakeRatios)
    

def calculate_sett_balances(badger,name,sett,currentBlock):
    settBalances = fetch_sett_balances(sett.address.lower(),currentBlock)
    geyserBalances = {}
    # Digg doesn't have a geyser so we have to ignore it 
    if name != "native.digg":
        geyserEvents = fetch_geyser_events(badger.getGeyser(name).address.lower(),currentBlock)
        geyserBalances = calc_balances_from_geyser_events(geyserEvents)

    balances = combine_balances(settBalances,geyserBalances)
    # TODO: whitelist certain contracts so they dont count for balances

    return convert_balances_to_usd(sett,balances)

def convert_balances_to_usd(sett,balances): 
    price = fetch_sett_price(sett.token().lower())
    ppfs = fetch_sett_ppfs(sett.token().lower())
    for account,bBalance in balances.items():
        balances[account] = price * bBalance * ppfs
    return balances