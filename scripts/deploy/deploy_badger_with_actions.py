#!/usr/bin/python3

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


def distribute_assets_to_users(badger, users, distributePair=True):
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

    assets = [badger.token]

    if distributePair:
        assets.append(badger.pair)

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
        if key == "native.badger":
            continue
        want = badger.getStrategyWant(key)
        farm = badger.getGeyser(key)
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

        # Deposit into Farms
        for user in users:
            shares = sett.balanceOf(user)
            sett.approve(farm, shares, {"from": user})
            farm.stake(shares // 2, "0x", {"from": user})

        print(deployer, accounts[1], accounts[2], sett.address)

        print(
            want.symbol(),
            key,
            getTokenMetadata(sett.token()),
            getTokenMetadata(want.address),
        )
        assert want.balanceOf(sett) > 0

        sett.earn({"from": deployer})

    chain.sleep(daysToSeconds(2))
    chain.mine()

    # Tend and harvest
    for key, sett in badger.sett_system.vaults.items():
        strategy = badger.getStrategy(key)
        if strategy.isTendable():
            strategy.tend({"from": deployer})
            chain.sleep(hours(0.5))
            chain.mine()
        strategy.harvest({"from": deployer})

    chain.sleep(daysToSeconds(1))
    chain.mine()

    for key, sett in badger.sett_system.vaults.items():
        if key == "native.badger":
            continue
        strategy = badger.getStrategy(key)
        if strategy.isTendable():
            strategy.tend({"from": deployer})
            chain.sleep(hours(0.5))
            chain.mine()
        strategy.harvest({"from": deployer})


def deploy_with_actions():
    badger = deploy_flow(test=True, print=True)

    testAccounts = [
        badger.deployer,
        accounts[1],
        accounts.at(
            web3.toChecksumAddress("0xe7bab002A39f9672a1bD0E949d3128eeBd883575"),
            force=False,
        ),
        accounts.at(
            web3.toChecksumAddress("0x482c741b0711624d1f462E56EE5D8f776d5970dC"),
            force=False,
        ),
    ]

    for account in testAccounts:
        accounts[0].transfer(account, Wei("10 ether"))

    print("Test: Run simulation")
    run_system_to_state(badger, testAccounts)
    print("Test: Setup complete")
    setts = [
        "native.renCrv",
        "native.badger",
        "native.sbtcCrv",
        "native.tbtcCrv",
        "harvest.renCrv",
    ]
    for settId in setts:
        sett = badger.getSett(settId)
        ppfs = sett.getPricePerFullShare()
        print("Initial PPFS ", Eth(ppfs))
    return badger


def main():
    deploy_with_actions()
    time.sleep(daysToSeconds(1))
