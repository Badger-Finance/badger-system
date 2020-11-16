#!/usr/bin/python3

from dotmap import DotMap
import pytest
from brownie import *

@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    # perform a chain rewind after completing each test, to ensure proper isolation
    # https://eth-brownie.readthedocs.io/en/v1.10.3/tests-pytest-intro.html#isolation-fixtures
    pass


# def timelock_unit(scope="module"):
#     unlockTime = chain.time() + 1000000
#     deployer = accounts[0]
#     team = [accounts[1], accounts[2], accounts[3]]
#     governor = accounts[5]
#     minnow = accounts[4]

#     tokenGifterAmount = Wei("500 ether")
#     tokenRequestAmount = Wei("100 ether")
#     transferAmount = Wei("500000 ether")

#     tokenGifter = TokenGifter.deploy()
#     ethGifter = EthGifter.deploy()

#     gToken = MockToken.deploy([tokenGifter, deployer], [
#                               tokenGifterAmount * 2, transferAmount * 10])

#     smartTimelock = SmartTimelock.deploy(
#         gToken.address, team[0], governor, unlockTime)

#     gToken.transfer(smartTimelock.address, transferAmount)

#     stakingMock = StakingMock.deploy(gToken.address)

#     deployer.transfer(ethGifter, Wei("10 ether"))

#     miscToken = MockToken.at([tokenGifter.address, smartTimelock.address], [
#                              tokenGifterAmount.mul(2), tokenGifterAmount])
