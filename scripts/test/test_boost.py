from brownie import *
from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger
from assistant.rewards.boost import badger_boost


def main():
    badger = connect_badger(badger_config.prod_json, load_deployer=False)
    badger_boost(badger, chain.height - 50)
