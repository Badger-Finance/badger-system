import json
from os import wait
import pytest

from brownie import *
from helpers.constants import *
from helpers.registry import registry
from rich.console import Console
from time import time, sleep

from scripts.actions.salary.salaries import fetch_salaries

console = Console()

badger_token = '0x3472A5A71965499acd81997a54BBA8D852C6E53d'
usdc_token = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'

@pytest.fixture(scope='function', autouse='True')
def setup():
    from assistant.rewards import rewards_assistant
    return rewards_assistant

# @pytest.mark.skip()
def test_salaries(setup):
    rewards_assistant = setup
    ContributorLogger = rewards_assistant.ContributorLogger

    admin, manager = accounts[:2]

    loggerContract = admin.deploy(ContributorLogger)
    loggerContract.initialize(admin, admin, manager)

    # salary period ends in the future
    console.print('\n[yellow]Testing a salary period that ends after the check is made[/yellow]')
    now = int(time()) + 1
    start_block = web3.eth.blockNumber
    first_entry = {
      'recipient': accounts[2].address,
      'token': badger_token,
      'amount': 100000,
      'amountDuration': 10,
      'startTime': now,
      'endTime': now + 10,
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

    wait_time = 5
    sleep(wait_time)
    chain.mine()
    end_block = web3.eth.blockNumber
    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # depending on when the block gets mined it could be +/- one second
    payouts = [
      int((wait_time) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime']))),
      int((wait_time + 1) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime']))),
      int((wait_time - 1) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime'])))
    ]
    expected_value1 = salary_json[first_entry['recipient']][first_entry['token']]
    assert (expected_value1 == payouts[0] or expected_value1 == payouts[1] or expected_value1 == payouts[2])

    start_block = web3.eth.blockNumber
    sleep(wait_time + 1)

    # checking after salary time ended
    console.print('[yellow]Testing that salary is correct after full period has elapsed[/yellow]')
    chain.mine()
    end_block = web3.eth.blockNumber
    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # depending on when the block gets mined it could be +/- one second
    payouts = [
      int((wait_time) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime']))),
      int((wait_time + 1) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime']))),
      int((wait_time - 1) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime'])))
    ]
    expected_value2 = salary_json[first_entry['recipient']][first_entry['token']]
    assert (expected_value2 == payouts[0] or expected_value2 == payouts[1] or expected_value2 == payouts[2])
    assert expected_value1 + expected_value2 == first_entry['amount']

    # multiple salaries in the same time period
    console.print('[yellow]Testing two salaries overlapping each other[/yellow]')
    now1 = int(time()) + 1
    start_block = web3.eth.blockNumber
    first_entry = {
      'recipient': accounts[2].address,
      'token': badger_token,
      'amount': 100000,
      'amountDuration': 5,
      'startTime': now1,
      'endTime': now1 + 5,
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
    now2 = int(time()) + 1
    second_entry = {
      'recipient': accounts[3].address,
      'token': badger_token,
      'amount': 650,
      'amountDuration': 10,
      'startTime': now2,
      'endTime': now2 + 10,
    }
    loggerContract.createEntry(
      second_entry['recipient'],
      second_entry['token'],
      second_entry['amount'],
      second_entry['amountDuration'],
      second_entry['startTime'],
      second_entry['endTime'],
      { 'from': manager }
    )

    wait_time = 8
    sleep(wait_time)
    chain.mine()
    end_block = web3.eth.blockNumber
    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # first address should have received entire payout
    assert salary_json[first_entry['recipient']][first_entry['token']] == first_entry['amount']

    # second address should have received a partial payout (may be off by +/- 1 second)
    payouts = [
      int((wait_time) * (second_entry['amount'] // (second_entry['endTime'] - second_entry['startTime']))),
      int((wait_time + 1) * (second_entry['amount'] // (second_entry['endTime'] - second_entry['startTime']))),
      int((wait_time - 1) * (second_entry['amount'] // (second_entry['endTime'] - second_entry['startTime'])))
    ]
    expected_value1 = salary_json[second_entry['recipient']][second_entry['token']]
    assert (expected_value1 == payouts[0] or expected_value1 == payouts[1] or expected_value1 == payouts[2])

    # after 5 more seconds there should only be one salary entry
    console.print('[yellow]Testing after the first period has ended[/yellow]')
    start_block = web3.eth.blockNumber

    wait_time = 5
    sleep(wait_time)
    chain.mine()
    end_block2 = web3.eth.blockNumber

    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block2, True)

    duration = second_entry['endTime'] - web3.eth.getBlock(end_block)['timestamp']
    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # should have received a partial payout
    expected_value2 = salary_json[second_entry['recipient']][second_entry['token']]
    payout = int((duration) * (second_entry['amount'] // (second_entry['endTime'] - second_entry['startTime'])))
    assert expected_value2 == payout
    assert expected_value1 + expected_value2 == second_entry['amount']

    # should be no more entries when called again
    console.print('[yellow]Testing with no more salaries to be paid out[/yellow]')
    start_block = web3.eth.blockNumber
    wait_time = 1
    sleep(wait_time)

    chain.mine()
    end_block = web3.eth.blockNumber
    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)
    with open(salary_json_filename) as f:
      salary_json = json.load(f)
    
    assert salary_json == {}

    # unlimited length salary period
    console.print('[yellow]Testing a salary period that lasts forever[/yellow]')
    now = int(time()) + 1
    start_block = web3.eth.blockNumber
    infinite_entry = {
      'recipient': accounts[3].address,
      'token': badger_token,
      'amount': 200000,
      'amountDuration': 10,
      'startTime': now,
      'endTime': 2**40-1,
    }
    tx = loggerContract.createEntry(
      infinite_entry['recipient'],
      infinite_entry['token'],
      infinite_entry['amount'],
      infinite_entry['amountDuration'],
      infinite_entry['startTime'],
      infinite_entry['endTime'],
      { 'from': manager }
    )

    id = tx.events['CreateEntry']['id']

    wait_time = 5
    sleep(wait_time)
    chain.mine()
    end_block = web3.eth.blockNumber

    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # depending on when the block gets mined it could be +/- one second
    payouts = [
      int((wait_time) * (infinite_entry['amount'] // (infinite_entry['amountDuration']))),
      int((wait_time + 1) * (infinite_entry['amount'] // (infinite_entry['amountDuration']))),
      int((wait_time - 1) * (infinite_entry['amount'] // (infinite_entry['amountDuration'])))
    ]
    expected_value1 = salary_json[infinite_entry['recipient']][infinite_entry['token']]
    assert (expected_value1 == payouts[0] or expected_value1 == payouts[1] or expected_value1 == payouts[2])

    # update entry
    console.print('[yellow]Testing updating salary period[/yellow]')
    now = int(time()) + 1
    wait_time = 5
    infinite_entry_updated = {
      'recipient': infinite_entry['recipient'],
      'token': infinite_entry['token'],
      'amount': 5555555,
      'amountDuration': 5,
      'startTime': now,
      'endTime': 2**40-1,
    }
    loggerContract.updateEntry(
      id,
      infinite_entry_updated['amount'],
      infinite_entry_updated['amountDuration'],
      infinite_entry_updated['startTime'],
      infinite_entry_updated['endTime'],
      { 'from': manager }
    )
    start_block = web3.eth.blockNumber
    sleep(wait_time)
    chain.mine()
    end_block = web3.eth.blockNumber

    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # depending on when the block gets mined it could be +/- one second
    payouts = [
      int((infinite_entry['amount'] // (infinite_entry['amountDuration']))) + int((wait_time + 1) * (infinite_entry_updated['amount'] // (infinite_entry_updated['amountDuration']))),
      int((infinite_entry['amount'] // (infinite_entry['amountDuration']))) + int((wait_time - 1) * (infinite_entry_updated['amount'] // (infinite_entry_updated['amountDuration']))),
      int((infinite_entry['amount'] // (infinite_entry['amountDuration']))) + int((wait_time) * (infinite_entry_updated['amount'] // (infinite_entry_updated['amountDuration'])))
    ]
    expected_value1 = salary_json[infinite_entry_updated['recipient']][infinite_entry_updated['token']]
    assert (expected_value1 == payouts[0] or expected_value1 == payouts[1] or expected_value1 == payouts[2])

    # delete an entry
    console.print('[yellow]Testing deletion[/yellow]')

    loggerContract.deleteEntry(id, { 'from': manager })
    start_block = web3.eth.blockNumber

    chain.mine()
    end_block = web3.eth.blockNumber
    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # might be 1 second worth of payouts depending on chain time
    payouts = [
      0,
      int((infinite_entry_updated['amount'] // (infinite_entry_updated['amountDuration'])))
    ]
    expected_value = salary_json[infinite_entry_updated['recipient']][infinite_entry_updated['token']]
    assert (expected_value == payouts[0] or expected_value == payouts[1])

    # update in the middle of a period
    console.print('[yellow]Testing update in the middle of a period[/yellow]')
    now1 = int(time()) + 1
    start_block = web3.eth.blockNumber
    wait_time = 5
    infinite_entry = {
      'recipient': accounts[4].address,
      'token': badger_token,
      'amount': 100000,
      'amountDuration': 10,
      'startTime': now1,
      'endTime': 2**40-1,
    }
    tx = loggerContract.createEntry(
      infinite_entry['recipient'],
      infinite_entry['token'],
      infinite_entry['amount'],
      infinite_entry['amountDuration'],
      infinite_entry['startTime'],
      infinite_entry['endTime'],
      { 'from': manager }
    )
    id = tx.events['CreateEntry']['id']
    sleep(wait_time)

    now2 = int(time()) + 1
    infinite_entry_updated = {
      'recipient': infinite_entry['recipient'],
      'token': infinite_entry['token'],
      'amount': 200000,
      'amountDuration': 10,
      'startTime': now2,
      'endTime': 2**40-1,
    }
    tx = loggerContract.updateEntry(
      id,
      infinite_entry_updated['amount'],
      infinite_entry_updated['amountDuration'],
      infinite_entry_updated['startTime'],
      infinite_entry_updated['endTime'],
      { 'from': manager }
    )

    sleep(wait_time+1)
    chain.mine()
    end_block = web3.eth.blockNumber

    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    payout = int((wait_time) * (infinite_entry['amount'] // (infinite_entry['amountDuration']))) + int((wait_time) * (infinite_entry_updated['amount'] // (infinite_entry_updated['amountDuration'])))
    expected_value = salary_json[infinite_entry_updated['recipient']][infinite_entry_updated['token']]
    assert payout <= expected_value <= 1.2 * payout

    # delete in middle of cycle
    console.print('[yellow]Testing deletion in middle of cycle[/yellow]')
    now = int(time()) + 1
    wait_time = 5
    id = tx.events['UpdateEntry']['updatedId']
    start_block = web3.eth.blockNumber
    sleep(wait_time)
    loggerContract.deleteEntry(id, { 'from': manager })

    sleep(wait_time)
    chain.mine()
    end_block = web3.eth.blockNumber

    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    expected_value = salary_json[infinite_entry_updated['recipient']][infinite_entry_updated['token']]
    payout = int((wait_time) * (infinite_entry_updated['amount'] // (infinite_entry_updated['amountDuration'])))
    assert payout <= expected_value <= 1.2 * payout
    
    # get paid in more than one token
    console.print('[yellow]Testing getting paid in more than one token[/yellow]')
    now = int(time()) + 1
    start_block = web3.eth.blockNumber
    first_entry = {
      'recipient': accounts[5].address,
      'token': badger_token,
      'amount': 100000,
      'amountDuration': 10,
      'startTime': now,
      'endTime': now + 10,
    }
    second_entry = {
      'recipient': accounts[5].address,
      'token': usdc_token,
      'amount': 100000,
      'amountDuration': 10,
      'startTime': now,
      'endTime': now + 10,
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
    loggerContract.createEntry(
      second_entry['recipient'],
      second_entry['token'],
      second_entry['amount'],
      second_entry['amountDuration'],
      second_entry['startTime'],
      second_entry['endTime'],
      { 'from': manager }
    )

    wait_time = 5
    sleep(wait_time)
    chain.mine()
    end_block = web3.eth.blockNumber
    salary_json_filename = fetch_salaries(loggerContract.address, start_block, end_block, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # depending on when the block gets mined it could be +/- one second
    payouts1 = [
      int((wait_time) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime']))),
      int((wait_time + 1) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime']))),
      int((wait_time - 1) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime'])))
    ]
    expected_value1 = salary_json[first_entry['recipient']][first_entry['token']]
    assert (expected_value1 == payouts1[0] or expected_value1 == payouts1[1] or expected_value1 == payouts1[2])

    payouts2 = [
      int((wait_time) * (second_entry['amount'] // (second_entry['endTime'] - second_entry['startTime']))),
      int((wait_time + 1) * (second_entry['amount'] // (second_entry['endTime'] - second_entry['startTime']))),
      int((wait_time - 1) * (second_entry['amount'] // (second_entry['endTime'] - second_entry['startTime'])))
    ]
    expected_value2 = salary_json[second_entry['recipient']][second_entry['token']]
    assert (expected_value2 == payouts2[0] or expected_value2 == payouts2[1] or expected_value2 == payouts2[2])