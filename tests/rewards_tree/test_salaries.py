import json
from os import wait
import secrets

import brownie
from dotmap import DotMap
import pytest
from decimal import Decimal

import pprint

from brownie import *
from helpers.constants import *
from helpers.registry import registry
from rich.console import Console
from time import time, sleep

from scripts.actions.salary.salaries import fetch_salaries

console = Console()

badger_token = '0x3472A5A71965499acd81997a54BBA8D852C6E53d'

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

    salary_json_filename = fetch_salaries(manager, loggerContract.address, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # depending on when the block gets mined it could be plus or minus one second
    payouts = [
      int((wait_time) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime']))),
      int((wait_time + 1) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime']))),
      int((wait_time - 1) * (first_entry['amount'] // (first_entry['endTime'] - first_entry['startTime'])))
    ]
    expected_value1 = salary_json[first_entry['recipient']][first_entry['token']]
    assert (expected_value1 == payouts[0] or expected_value1 == payouts[1] or expected_value1 == payouts[2])

    sleep(wait_time + 1)

    # checking after salary time ended
    console.print('[yellow]Testing that salary is correct after full period has elapsed[/yellow]')
    salary_json_filename = fetch_salaries(manager, loggerContract.address, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # depending on when the block gets mined it could be one second off
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

    salary_json_filename = fetch_salaries(manager, loggerContract.address, True)

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
    last_paid_timestamp = loggerContract.lastPaidTimestamp()
    wait_time = 5
    sleep(wait_time)

    salary_json_filename = fetch_salaries(manager, loggerContract.address, True)

    duration = second_entry['endTime'] - last_paid_timestamp
    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # should have received a partial payout
    expected_value2 = salary_json[second_entry['recipient']][second_entry['token']]
    payout = int((duration) * (second_entry['amount'] // (second_entry['endTime'] - second_entry['startTime'])))
    assert expected_value2 == payout
    assert expected_value1 + expected_value2 == second_entry['amount']

    # should be no more entries when called again
    console.print('[yellow]Testing with no more salaries to be paid out[/yellow]')
    wait_time = 1
    sleep(wait_time)

    salary_json_filename = fetch_salaries(manager, loggerContract.address, True)
    with open(salary_json_filename) as f:
      salary_json = json.load(f)
    
    assert salary_json == {}

    # unlimited length salary period
    console.print('[yellow]Testing a salary period that lasts forever[/yellow]')
    now = int(time()) + 1
    infinite_entry = {
      'recipient': accounts[3].address,
      'token': badger_token,
      'amount': 200000,
      'amountDuration': 10,
      'startTime': now,
      'endTime': 2**256-1,
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

    salary_json_filename = fetch_salaries(manager, loggerContract.address, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # depending on when the block gets mined it could be plus or minus one second
    payouts = [
      int((wait_time) * (infinite_entry['amount'] // (infinite_entry['amountDuration']))),
      int((wait_time + 1) * (infinite_entry['amount'] // (infinite_entry['amountDuration']))),
      int((wait_time - 1) * (infinite_entry['amount'] // (infinite_entry['amountDuration'])))
    ]
    expected_value1 = salary_json[infinite_entry['recipient']][infinite_entry['token']]
    assert (expected_value1 == payouts[0] or expected_value1 == payouts[1] or expected_value1 == payouts[2])

    # update entry
    console.print('[yellow]Testing updating salary period[/yellow]')
    infinite_entry_updated = {
      'recipient': infinite_entry['recipient'],
      'token': infinite_entry['token'],
      'amount': 5555555,
      'amountDuration': 5,
      'startTime': now,
      'endTime': 2**256-1,
    }
    loggerContract.updateEntry(
      id,
      infinite_entry_updated['amount'],
      infinite_entry_updated['amountDuration'],
      infinite_entry_updated['startTime'],
      infinite_entry_updated['endTime'],
      { 'from': manager }
    )

    wait_time = 5
    sleep(wait_time)

    salary_json_filename = fetch_salaries(manager, loggerContract.address, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    # depending on when the block gets mined it could be plus or minus one second
    payouts = [
      int((wait_time) * (infinite_entry_updated['amount'] // (infinite_entry_updated['amountDuration']))),
      int((wait_time + 1) * (infinite_entry_updated['amount'] // (infinite_entry_updated['amountDuration']))),
      int((wait_time - 1) * (infinite_entry_updated['amount'] // (infinite_entry_updated['amountDuration'])))
    ]
    expected_value1 = salary_json[infinite_entry_updated['recipient']][infinite_entry_updated['token']]
    assert (expected_value1 == payouts[0] or expected_value1 == payouts[1] or expected_value1 == payouts[2])

    # delete an entry
    console.print('[yellow]Testing deletion[/yellow]')

    loggerContract.deleteEntry(id, { 'from': manager })

    salary_json_filename = fetch_salaries(manager, loggerContract.address, True)

    with open(salary_json_filename) as f:
      salary_json = json.load(f)

    assert salary_json == {}