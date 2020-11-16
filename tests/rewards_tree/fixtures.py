#!/usr/bin/python3
import pytest
from brownie import *
from dotmap import DotMap

@pytest.fixture(scope="module")
def rewards_tree_unit(scope="module"):
    deployer = accounts[0]
    rootUpdater = accounts[1]
    guardian = accounts[2]

    system = DotMap(
        badgerTree=BadgerTree.deploy(deployer, rootUpdater, guardian, {'from': deployer}),
        deployer=accounts[0],
        rootUpdater=accounts[1],
        guardian=accounts[2],
        rewardsTokens=[]
    )

    for i in range(0,4):
        system.rewardsToken.push(MockToken.deploy([deployer], [Wei("100000000 ether")], {'from': deployer}))

    yield system