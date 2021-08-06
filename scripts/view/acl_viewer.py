from helpers.token_utils import print_balances, to_token
from brownie import *
from helpers.time_utils import hours, to_utc_date
from tabulate import tabulate
from helpers.registry import registry
from helpers.console_utils import console
from helpers.constants import *

def print_role_list(contract, role, members, name=""):
    table = []
    if name == "":
        console.print(f"[blue]=== {role} for {contract} ===[/blue]")
    else:
        console.print(f"[blue]=== {name} for {contract} ===[/blue]")
    for member in members:
        table.append([member])
    print(tabulate(table))

def print_access_control(contract):
    '''
    Print all role holders for a contract
    '''
    for name, hex in role_registry.roles.items():
        role_members = []
        count = contract.getRoleMemberCount(hex)
        print(name, count)
        if count > 0:
            for i in range (0, count):
                account = contract.getRoleMember(hex, i)
                role_members.append(account)
        
            print_role_list(contract, hex, role_members, name=name)

def main():
    contracts_to_view = [interface.IAccessControl("0x711A339c002386f9db409cA55b6A35a604aB6cF6")]

    for contract in contracts_to_view:
        print_access_control(contract)
