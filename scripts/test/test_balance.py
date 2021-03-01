
from brownie import *
from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger
from assistant.rewards.balance import get_balance_data
def main():
    badger = connect_badger(badger_config.prod_json,load_deployer=False)
    get_balance_data(badger)
    
