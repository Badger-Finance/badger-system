from helpers.time_utils import daysToSeconds
import os
import json
from scripts.systems.badger_system import connect_badger
import warnings
from tabulate import tabulate
from brownie import *
from helpers.registry import registry

warnings.simplefilter("ignore")
# keeper = accounts.load("keeper")

def val(amount):
    return "∫{:,.2f}".format(amount / 1e18)

def main():
    test = False
    # if rpc.is_active():
    #     sender = accounts[0]
    # else:
    #     priv = os.environ.get('VAULT_KEEPER_PRIV')
    #     sender = accounts.add(priv) if priv else accounts.load(input('brownie account: '))
    fileName = "deploy-" + str(chain.id) + ".json"
    badger = connect_badger(fileName)
    token = badger.token

    deployer = accounts.load("badger_deployer")
    badger.teamVesting.release({'from': deployer})

