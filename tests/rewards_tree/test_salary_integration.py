import json
from os import wait
import pytest

from brownie import *
from helpers.constants import *
from helpers.registry import registry
from rich.console import Console
from time import time, sleep
from dotmap import DotMap

from scripts.actions.salary.salaries import fetch_salaries
from tests.helpers import distribute_from_whales

console = Console()

badger_token = '0x3472A5A71965499acd81997a54BBA8D852C6E53d'
digg_token = '0x798D1bE841a82a273720CE31c822C61a67a601C3'

# generates merkle root purely off dummy data
def internal_generate_rewards_in_range(rewards_assistant, newRewards, startBlock, endBlock, pastRewards):
    cumulativeRewards = rewards_assistant.process_cumulative_rewards(pastRewards, newRewards)
    merkleTree = rewards_assistant.rewards_to_merkle_tree(cumulativeRewards, startBlock, endBlock, newRewards)
    rootHash = rewards_assistant.hash(merkleTree["merkleRoot"])

    return {
        "merkleTree": merkleTree,
        "rootHash": rootHash,
    }

@pytest.fixture(scope='function', autouse='True')
def setup():
    from assistant.rewards import rewards_assistant
    return rewards_assistant

# @pytest.mark.skip()
def test_salaries(setup):
    rewards_assistant = setup
    admin, proposer, manager, validator, user = accounts[:5]

    # setup salary contract
    ContributorLogger = rewards_assistant.ContributorLogger

    loggerContract = admin.deploy(ContributorLogger)
    loggerContract.initialize(admin, admin, manager)

    # setup rewards tree
    BadgerTreeV2 = rewards_assistant.BadgerTreeV2
    guardian = rewards_assistant.guardian
    rootUpdater = rewards_assistant.rootUpdater

    rewardsContract = admin.deploy(BadgerTreeV2)
    rewardsContract.initialize(admin, proposer, validator)

    # distribute tokens to rewards contract
    distribute_from_whales(rewardsContract, accounts[4])

    # test claiming a salary from the tree
    now = int(time()) + 1
    start_block = web3.eth.blockNumber
    wait_time = 5
    first_entry = {
      'recipient': user.address,
      'token': badger_token,
      'amount': 100000,
      'amountDuration': 10,
      'startTime': now,
      'endTime': 2**40-1,
    }
    loggerContract.createEntry(
      first_entry['recipient'],
      first_entry['token'],
      first_entry['amount'],
      first_entry['amountDuration'],
      first_entry['startTime'],
      first_entry['endTime'],
      { 'from': manager }
    )

    sleep(wait_time)
    chain.mine()
    end_block = web3.eth.blockNumber
    expected_total = first_entry['amount'] / first_entry['amountDuration'] * wait_time

    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)
    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    startBlock = rewardsContract.lastPublishStartBlock() + 1
    endBlock = startBlock + 5
    currCycle = rewardsContract.currentCycle()
    nextCycle = currCycle + 1

    geyserRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': salary_json,
        "tokens": [
            salary_json[first_entry['recipient']].keys()
        ],
        'cycle': nextCycle
    })
    pastRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {},
        "tokens": [],
        'cycle': currCycle
    })

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        geyserRewards,
        startBlock, 
        endBlock, 
        pastRewards
    )

    rewardsContract.proposeRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": proposer}
    )
    rewardsContract.approveRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": validator}
    )

    # attempt to claim salary in two partial claims
    rewardsContract.claim(
        rewards_data["merkleTree"]['claims'][first_entry['recipient']]['tokens'],
        rewards_data["merkleTree"]['claims'][first_entry['recipient']]['cumulativeAmounts'],
        rewards_data["merkleTree"]['claims'][first_entry['recipient']]['index'],
        rewards_data["merkleTree"]['claims'][first_entry['recipient']]['cycle'],
        rewards_data["merkleTree"]['claims'][first_entry['recipient']]['proof'],
        [
            expected_total // 2
        ],
        {'from': first_entry['recipient']}
    )
    rewardsContract.claim(
        rewards_data["merkleTree"]['claims'][first_entry['recipient']]['tokens'],
        rewards_data["merkleTree"]['claims'][first_entry['recipient']]['cumulativeAmounts'],
        rewards_data["merkleTree"]['claims'][first_entry['recipient']]['index'],
        rewards_data["merkleTree"]['claims'][first_entry['recipient']]['cycle'],
        rewards_data["merkleTree"]['claims'][first_entry['recipient']]['proof'],
        [
            expected_total // 2
        ],
        {'from': first_entry['recipient']}
    )