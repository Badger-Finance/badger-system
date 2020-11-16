import pytest
from brownie import * 
from dotmap import DotMap

def get_token_balances(accounts, tokens):
    balances = DotMap()
    for token in tokens:
        for account in accounts:
            balances.token.account = token.balanceOf(account)
    return balances