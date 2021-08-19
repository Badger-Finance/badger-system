from brownie import *
from tabulate import tabulate
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
    contracts_to_view = [interface.IAccessControl("0x711a339c002386f9db409ca55b6a35a604ab6cf6")]

    for contract in contracts_to_view:
        print_access_control(contract)
