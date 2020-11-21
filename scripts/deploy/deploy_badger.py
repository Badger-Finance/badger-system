#!/usr/bin/python3

from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from scripts.systems.badger_system import deploy_badger, config_badger, start_rewards
from brownie import *
from config.badger_config import config
from helpers.registry import registry
from scripts.systems.aragon_system import connect_aragon
from dotmap import DotMap


def connect_deps():
    aragon = connect_aragon()
    gnosis_safe = connect_gnosis_safe()
    print(aragon)
    return DotMap(aragon=aragon, gnosis_safe=gnosis_safe)


def main():
    """
    Deploy Badger System
    """
    systems = connect_deps()
    badger = deploy_badger(systems, accounts[0])
    print("Badger System Deployed")
    config_badger(badger)
    start_rewards(badger)
    print("Badger System Setup Complete")
    return badger
