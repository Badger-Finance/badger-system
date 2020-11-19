# import pytest
# from brownie import *
# from tests.badger_timelock.fixtures import timelock_unit


# @pytest.fixture(scope="function", autouse="True")
# def setup(timelock_unit):
#     return timelock_unit


# def test_transfer_eth(setup):
#     ethGifter = setup.ethGifter
#     deployer = setup.deployer
#     smartTimelock = setup.smartTimelock
#     team = setup.team

#     ethAmount = Wei("1 ether")

#     preBalances = {
#         "ethGifter": ethGifter.balance(),
#         "deployer": deployer.balance(),
#     }

#     ethGifter.requestEth(ethAmount)

#     postBalances = {
#         "ethGifter": ethGifter.balance(),
#         "deployer": deployer.balance(),
#     }

#     assert postBalances["ethGifter"] == preBalances["ethGifter"] - (ethAmount)

#     preBalances = {
#         "ethGifter": ethGifter.balance(),
#         "deployer": deployer.balance(),
#         "timelock": smartTimelock.balance(),
#     }

#     smartTimelock.call(
#         ethGifter, 0, ethGifter.requestEth.encode_input(ethAmount), {"from": team[0]}
#     )

#     postBalances = {
#         "ethGifter": ethGifter.balance(),
#         "deployer": deployer.balance(),
#         "timelock": smartTimelock.balance(),
#     }

#     assert postBalances["ethGifter"] == preBalances["ethGifter"] - (ethAmount)
#     assert postBalances["timelock"] == preBalances["timelock"] + (ethAmount)


# def test_recieve_eth(setup):
#     smartTimelock = setup.smartTimelock
#     deployer = setup.deployer
#     team = setup.team

#     ethAmount = Wei("1 ether")

#     preBalances = {
#         "timelock": smartTimelock.balance(),
#         "deployer": deployer.balance(),
#     }

#     deployer.transfer(smartTimelock, ethAmount)

#     postBalances = {
#         "timelock": smartTimelock.balance(),
#         "deployer": deployer.balance(),
#     }

#     assert postBalances["deployer"] <= preBalances["deployer"] - ethAmount
#     assert postBalances["timelock"] == preBalances["timelock"] + ethAmount

#     preBalances = {
#         "team0": team[0].balance(),
#         "deployer": deployer.balance(),
#     }

#     smartTimelock.call(deployer, ethAmount, "0x", {"from": team[0], "value": ethAmount})

#     postBalances = {
#         "team0": team[0].balance(),
#         "deployer": deployer.balance(),
#     }

#     assert postBalances["deployer"] == preBalances["deployer"] + ethAmount
#     assert postBalances["team0"] <= preBalances["team0"] - ethAmount
