from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from helpers.time_utils import daysToSeconds, hours
import os
import json
from scripts.systems.badger_system import connect_badger
import warnings
from tabulate import tabulate
from brownie import *
from helpers.registry import registry
from rich.console import Console

console = Console()


def confirm_blacksmith_contract(contract):
    return False


def confirm_balances(badger, blacksmith):
    return False


def main():
    test = True
    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName)

    coverage_expire_timestamp = 1614470400  # 2/28/2021 12:00 AM UTC
    rewards_expire_timestamp = coverage_expire_timestamp - daysToSeconds(
        1
    )  # 2/27/2021 12:00 AM UTC
    print(rewards_expire_timestamp, 1614384000)
    assert rewards_expire_timestamp == 1614384000

    multisig = badger.devMultisig
    deployer = badger.deployer
    rewardsEscrow = badger.rewardsEscrow

    convert_to_test_mode(multisig)

    blacksmith = Contract.from_explorer("0xe0b94a7bb45dd905c79bb1992c9879f40f1caed5")
    confirm_blacksmith_contract(blacksmith)

    claimAmount = Wei("46875 ether")
    noClaimAmount = Wei("78125 ether")

    claimLp = Contract.from_explorer("0xbad3ca7e741f785a05d7b3394db79fcc4b6d85af")
    noClaimLp = Contract.from_explorer("0xa553c12ab7682efda28c47fdd832247d62788273")

    total = claimAmount + noClaimAmount

    assert total == Wei("125000 ether")

    # Approve blacksmith as valid recipient
    data = badger.rewardsEscrow.approveRecipient.encode_input(blacksmith)
    exec_direct(multisig, {"to": rewardsEscrow.address, "data": data}, deployer)

    print("ove blacksmith as valid recipient")
    print(rewardsEscrow.address)
    print(data)

    # Approve BADGER token as valid recipient
    data = badger.rewardsEscrow.approveRecipient.encode_input(badger.token)
    exec_direct(multisig, {"to": rewardsEscrow.address, "data": data}, deployer)

    print("Approve BADGER token as valid recipient")
    print(rewardsEscrow.address)
    print(data)

    # Approve blacksmith to take appropriate BADGER amount
    call = badger.token.approve.encode_input(blacksmith, total)

    data = badger.rewardsEscrow.call.encode_input(badger.token, 0, call)

    exec_direct(multisig, {"to": rewardsEscrow.address, "data": data}, deployer)

    print("Approve blacksmith to take appropriate BADGER amount")
    print(rewardsEscrow.address)
    print(call)
    print(data)

    assert badger.token.allowance(rewardsEscrow, blacksmith) == total

    startTime = 1607293800
    endTime = rewards_expire_timestamp
    print (chain.time())
    assert startTime - chain.time() > 0
    assert startTime - chain.time() < hours(2)

    # Transfer CLAIM amount to blacksmith
    call = blacksmith.addBonusToken.encode_input(
        claimLp, badger.token, startTime, endTime, claimAmount
    )

    data = badger.rewardsEscrow.call.encode_input(blacksmith, 0, call)

    exec_direct(multisig, {"to": rewardsEscrow.address, "data": data}, deployer)

    print("Transfer CLAIM amount to blacksmith")
    print(rewardsEscrow.address)
    print(call)
    print(data)

    assert badger.token.balanceOf(blacksmith) == claimAmount

    # Transfer NOCLAIM amount to blacksmith
    print("Transfer NOCLAIM amount to blacksmith")

    call = blacksmith.addBonusToken.encode_input(
        noClaimLp, badger.token, startTime, endTime, noClaimAmount
    )

    data = badger.rewardsEscrow.call.encode_input(blacksmith, 0, call)
    exec_direct(multisig, {"to": rewardsEscrow.address, "data": data}, deployer)

    print("Transfer NOCLAIM amount to blacksmith")
    print(rewardsEscrow.address)
    print(call)
    print(data)

    assert badger.token.balanceOf(blacksmith) == total

