from brownie import *
from rich.console import Console
from assistant.subgraph.client import fetch_sett_balances,fetch_geyser_events
from assistant.rewards.calc_harvest import combine_balances,calc_balances_from_geyser_events
console = Console()

APPROVED_CONTRACTS = {}

def get_balance_data(badger,currentBlock):
    allSetts = badger.sett_system.vaults
    console.log(allSetts)
    diggSetts = []
    badgerSetts = []
    nonNativeSetts = []
    for name,sett in allSetts.items():
        balances = calculate_sett_balances(badger,name,sett,currentBlock)
        data = {}
        data[name] = balances
        if name in ["native.uniDiggWbtc","native,sushiDiggWbtc","native.digg"]:
            diggSetts.append(data)
        elif name in ["native.badger","native.uniBadgerWbtc","native.sushiBadgerWbtc"]:
            badgerSetts.append(data)
        else:
            nonNativeSetts.append(data)


def calculate_sett_balances(badger,name,sett,currentBlock):
    settBalances = fetch_sett_balances(sett.address.lower(),currentBlock)
    console.log(len(settBalances))
    console.log(name)
    geyserBalances = {}
    # Digg doesn't have a geyser so we have to ignore it 
    if name != "native.digg":
        geyserEvents = fetch_geyser_events(badger.getGeyser(name).address.lower(),currentBlock)
        geyserBalances = calc_balances_from_geyser_events(geyserEvents)

    balances = combine_balances(settBalances,geyserBalances)
    console.log(balances)

    for from_contract,to_contract in APPROVED_CONTRACTS:
        if contract in balances:
            amount = balances[from_contract]
            balances[contract] = 0
            # The address that stores the bToken might not be able 
            # to claim so we they should provide an address that can
            # claim on their behalf
            balances[to_contract] = amount
    return balances
    

    # Convert token to usd

    