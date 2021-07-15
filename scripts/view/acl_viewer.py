from helpers.token_utils import print_balances, to_token
from brownie import *
from config.badger_config import badger_config
from helpers.time_utils import hours, to_utc_date
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from helpers.registry import registry
from helpers.console_utils import console
from helpers.constants import *


def print_role_list(contract, role, members, name=""):
    table = []
    if name == "":
        console.print(f"[blue]=== Role Members: {role} for {contract} ===[/blue]")
    else:
        console.print(f"[blue]=== Role Members: {name} for {contract} ===[/blue]")
    for member in members:
        table.append([member])
    print(tabulate(table, ["address"]))

def print_access_control(contract):
    '''
    Print all role holders for a contract
    '''
    for name, hex in role_registry.roles.items():
        role_members = []
        count = contract.getRoleMemberCount(hex)
        if count > 0:
            for i in range (0, count):
                account = contract.getRoleMember(hex, i)
                role_members.append(account)
        
            print_role_list(contract, hex, role_members, name=name)

def main():
    badger = connect_badger()
    print_access_control(badger.badgerTree)
