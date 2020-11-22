#!/usr/bin/python3

from tests.helpers import balances, getTokenMetadata
import time
from helpers.time_utils import daysToSeconds
from helpers.constants import APPROVED_STAKER_ROLE
from tests.conftest import create_uniswap_pair, distribute_from_whales
from scripts.systems.badger_system import (
    BadgerSystem,
    print_to_file,
)
from brownie import *
from helpers.registry import registry
from dotmap import DotMap
from config.badger_config import badger_config, badger_total_supply
from scripts.deploy.deploy_badger import (
    test_deploy,
    start_staking_rewards,
    post_deploy_config,
)
from helpers.registry import whale_registry


def distribute_assets_to_users(badger, users):
    deployer = badger.deployer
    numUsers = len(users) + 1

    for key, whale in whale_registry.items():
        print(whale.token)
        if whale.token:
            for user in users:
                token = interface.IERC20(whale.token)
                token.transfer(
                    user, token.balanceOf(deployer) // numUsers, {"from": deployer}
                )

    assets = [badger.token, badger.pair]

    for asset in assets:
        for user in users:
            token = interface.IERC20(asset)
            token.transfer(
                user, token.balanceOf(deployer) // numUsers, {"from": deployer}
            )


def run_system_to_state(badger: BadgerSystem, users):
    print("Distribute assets between users")
    distribute_assets_to_users(badger, users)
    deployer = badger.deployer

    for key, sett in badger.sett_system.vaults.items():
        want = badger.getStrategyWant(key)
        assert want == sett.token()

        # Deposit into Setts
        for user in users:
            balance = want.balanceOf(user)
            want.approve(sett, balance, {"from": user})
            tx = sett.deposit(balance // 3, {"from": user}) 
            

        balances(
            {
                "deployer": deployer,
                "user 1": accounts[1],
                "user 2": accounts[2],
                "sett": sett,
            },
            [want, badger.token, sett],
        )

        print(deployer, accounts[1], accounts[2], sett.address)

        print(want.symbol(), key, getTokenMetadata(sett.token()), getTokenMetadata(want.address))
        assert want.balanceOf(sett) > 0

        sett.earn({"from": deployer})

    chain.sleep(daysToSeconds(2))
    chain.mine()

    for key, sett in badger.sett_system.vaults.items():
        strategy = badger.getStrategy(key)
        if strategy.isTendable():
            strategy.tend({"from": deployer})
            chain.mine()
        strategy.harvest({"from": deployer})

    chain.sleep(daysToSeconds(1))
    chain.mine()

    for key, sett in badger.sett_system.vaults.items():
        strategy = badger.getStrategy(key)
        if strategy.isTendable():
            strategy.tend({"from": deployer})
            chain.mine()
        strategy.harvest({"from": deployer})


def deploy_with_actions():
    badger = test_deploy()
    print("Test: Badger System Deployed")
    post_deploy_config(badger)
    start_staking_rewards(badger)
    print("Test: Badger System Setup Complete")
    print("Printing contract addresses to local.json")
    print_to_file(badger, "local.json")

    print("Test: Run simulation")
    run_system_to_state(badger, [accounts[1], accounts[2]])
    print("Test: Setup complete")
    return badger


def main():
    deploy_with_actions()
