import os
import json
from scripts.systems.badger_system import connect_badger
import warnings
from tabulate import tabulate
from brownie import interface, accounts, rpc, VaultKeeper

with open("local.json") as f:
    badger_deploy = json.load(f)

warnings.simplefilter('ignore')
keeper = accounts.load('keeper')

skipped = []

setts = badger_deploy['sett_system']['vaults']
badger = connect_badger(badger_deploy)

def check_earn(sett, strategy):
    """
    Run earn() if sufficent deposits in Sett
    """


def check_harvest(sett, strategy):
    """
    - Run harvest() if sufficent value accumulated
    - TODO How to 
    """

def check_tend(sett, strategy):
    """
    - Run tend() if sufficient value accumulated
    """

def main():
    if rpc.is_active():
        sender = accounts[0]
    else:
        priv = os.environ.get('VAULT_KEEPER_PRIV')
        sender = accounts.add(priv) if priv else accounts.load(input('brownie account: '))

    table = []
    vaults = []
    for data in badger_deploy:
        if data['name'] in skipped:
            print('aLINK not supported yet')
            continue
        token = interface.ERC20(data['erc20address'])
        vault = interface.YearnVault(data['vaultContractAddress'])
        decimals = token.decimals()
        available = vault.available()
        balance = vault.balance()
        ratio = 1 - vault.min() / vault.max()
        can_earn = available / balance > ratio if balance > 0 else False
        if can_earn:
            vaults.append(data['vaultContractAddress'])
        table.append([data['name'], available / 10**decimals, balance / 10**decimals, can_earn])
    
    print(tabulate(table, headers=['name', 'available', 'balance', 'can_earn']))

    if vaults:
        print('poking these vaults:', vaults)
        keeper.earn(vaults, {'from': sender, 'gas_limit': 2_500_000})
    else:
        print('no vaults to poke, exiting')