#!/usr/bin/python3
from helpers.proxy_utils import deploy_proxy
import pytest
from brownie import *
from dotmap import DotMap
from helpers.constants import *


@pytest.fixture(scope="module")
def rewards_tree_unit():
    deployer = accounts[0]
    rootUpdater = accounts[1]
    guardian = accounts[2]

    badgerTreeLogic = BadgerTree.deploy({"from": deployer})
    mockTokenLogic = MockToken.deploy({"from": deployer})
    badgerGeyserLogic = BadgerGeyser.deploy({"from": deployer})

    system = DotMap(
        deployer=accounts[0],
        rootUpdater=accounts[1],
        guardian=accounts[2],
        stakingToken=deploy_proxy(
            "MockToken",
            MockToken.abi,
            mockTokenLogic.address,
            AddressZero,
            mockTokenLogic.initialize.encode_input(
                [deployer.address], [Wei("100000000 ether")]
            ),
            deployer,
        ),
        rewardsTokens=[],
        geysers=[],
    )

    system.badgerTree = deploy_proxy(
        "BadgerTree",
        BadgerTree.abi,
        badgerTreeLogic.address,
        AddressZero,
        badgerTreeLogic.initialize.encode_input(deployer, rootUpdater, guardian),
        deployer,
    )

    for i in range(0, 4):
        token = deploy_proxy(
            "MockToken",
            MockToken.abi,
            mockTokenLogic.address,
            AddressZero,
            mockTokenLogic.initialize.encode_input(
                [deployer.address], [Wei("100000000 ether")]
            ),
            deployer,
        )
        system.rewardsTokens.append(token)

        geyser = deploy_proxy(
            "BadgerGeyser",
            BadgerGeyser.abi,
            badgerGeyserLogic.address,
            AddressZero,
            badgerGeyserLogic.initialize.encode_input(
                system.stakingToken, token, chain.time(), deployer, deployer
            ),
            deployer,
        )
        system.geysers.append(geyser)

    yield system
