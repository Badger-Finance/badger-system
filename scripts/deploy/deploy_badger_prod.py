#!/usr/bin/python3

from scripts.deploy.confirm_deploy import confirm_deploy
import time

from brownie import *
from config.badger_config import badger_config, badger_total_supply
from dotmap import DotMap
from helpers.registry import registry, whale_registry
from helpers.time_utils import daysToSeconds, hours
from helpers.utils import Eth
from scripts.deploy.deploy_badger import (
    deploy_flow,
    post_deploy_config,
    start_staking_rewards,
    test_deploy,
)
from scripts.systems.badger_system import BadgerSystem, print_to_file
from tests.helpers import balances, getTokenMetadata

def main():
    badger = deploy_flow(test=False, outputToFile=True, uniswap=False)
    # confirm_deploy(badger)
    time.sleep(daysToSeconds(1))

