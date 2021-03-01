from brownie import *
from rich.console import Console
from assistant.subgraph.client import fetch_sett_balances,fetch_geyser_events,fetch_sett_token_prices_usd
from assistant.rewards.calc_harvest import combine_balances
console = Console()

APPROVED_CONTRACTS = {}

def get_balance_data(badger,currentBlock):
    allSetts = badger.sett_system.vaults
    console.log(allSetts)
    diggSetts = []
    badgerSetts = []
    nonNativeSetts = []
    for name,sett in allSetts.items():
        console.log(sett.token)
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
    geyserBalances = calc_balances_from_geyser_events(fetch_geyser_events(badger.getGeyser(name),startBlock))
    balances = combine_balances(settBalances,geyserBalances)
    token_prices = fetch_sett_token_prices_usd()

    for from_contract,to_contract in APPROVED_CONTRACTS:
        if contract in settBalances:
            amount = settBalances[from_contract]
            settBalances[contract] = 0
            # Where we should send the rewards 
            # The address that stores the bToken might not be able 
            # to claim so we they should provide an address that can
            # claim on their behalf
            settBalances[to_contract] = amount

    # Convert token to usd

    