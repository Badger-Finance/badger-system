
from brownie import *
from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger
from assistant.rewards.boost import get_balance_data
from assistant.subgraph.client import fetch_cream_bbadger_deposits
def main():
    #fetch_cream_bbadger_deposits()
    badger = connect_badger(badger_config.prod_json,load_deployer=False)
    get_balance_data(badger,chain.height - 50)
