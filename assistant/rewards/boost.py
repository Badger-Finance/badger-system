from brownie import *
from rich.console import Console
from assistant.subgraph.client import (
    fetch_sett_balances, 
    fetch_geyser_events, 
    fetch_cream_bbadger_deposits
)
from assistant.rewards.rewards_utils import (
    combine_balances,
    calc_balances_from_geyser_events,
    fetch_sett_price,
    fetch_sett_ppfs
)
console = Console()

APPROVED_CONTRACTS = {}

def get_balance_data(badger,currentBlock):
    allSetts = badger.sett_system.vaults
    console.log(allSetts)
    diggSetts = []
    badgerSetts = []
    nonNativeSetts = []
    for name,sett in allSetts.items():
        balances = calculate_sett_balances_usd(badger,name,sett,currentBlock)
        data = {}
        data[name] = balances
        if name in ["native.uniDiggWbtc","native.sushiDiggWbtc","native.digg"]:
            diggSetts.append(data)
        elif name in ["native.badger","native.uniBadgerWbtc","native.sushiBadgerWbtc"]:
            badgerSetts.append(data)
        else:
            nonNativeSetts.append(data)
    
    # Include bBadger deposits on CREAM
    badgerSetts.append({
        "crBBADGER": fetch_cream_bbadger_deposits()
    })


def calculate_sett_balances(badger,name,sett,currentBlock):
    settBalances = fetch_sett_balances(sett.address.lower(),currentBlock)
    geyserBalances = {}
    # Digg doesn't have a geyser so we have to ignore it 
    if name != "native.digg":
        geyserEvents = fetch_geyser_events(badger.getGeyser(name).address.lower(),currentBlock)
        geyserBalances = calc_balances_from_geyser_events(geyserEvents)

    balances = combine_balances(settBalances,geyserBalances)
    # TODO: whitelist certain contracts so they dont count for balances
    # TODO: Use extra subgraphs to determine seperate balances

    return convert_balances_to_usd(sett,balances)

    # Convert token to usd

def convert_balances_to_usd(sett,balances): 
    price = fetch_sett_price(sett.token().lower())
    ppfs = fetch_sett_ppfs(sett.token().lower())
    for account,bBalance in balances.items():
        balances[account] = price * bBalance * ppfs
    return balances

    