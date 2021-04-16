from brownie.network import web3
from brownie.network.account import Account
from scripts.systems.badger_system import connect_badger
from time import time 
from datetime import datetime

from helpers.multicall.call import Call
from helpers.multicall.multicall import Multicall

import json
import brownie
import os

def __get_data__(logger_address: str, start: int, end: int):
  calls = [Call(logger_address, ['getEntry(uint256)(address,address,uint256,uint256,uint256,uint256)', i], [['recipient_'+str(i), None], ['token_'+str(i), None], ['amount_'+str(i), None], ['amountDuration_'+str(i), None], ['startTime_'+str(i), None], ['endTime_'+str(i), None]]) for i in range(start, end)]
  multi = Multicall(calls)()

  result = []
  for i in range(start, end):
    result.append((
      web3.toChecksumAddress(multi['recipient_'+str(i)]),
      web3.toChecksumAddress(multi['token_'+str(i)]),
      multi['amount_'+str(i)],
      multi['amountDuration_'+str(i)],
      multi['startTime_'+str(i)],
      multi['endTime_'+str(i)]
    ))
  return result


def fetch_salaries(manager: Account, logger_address: str, test=False):
  with open('build/contracts/ContributorLogger.json') as f:
    logger_abi = json.load(f)['abi']

  logger_contract = brownie.Contract.from_abi('ContributorLogger', logger_address, logger_abi)

  next_id = logger_contract.nextId()
  last_paid_timestamp = logger_contract.lastPaidTimestamp()
  first_paid_index = logger_contract.firstPaidIndex()

  entries = __get_data__(logger_address, first_paid_index, next_id)

  updated_first_paid_index = first_paid_index
  salaries = dict()
  now = int(time())

  for entry in entries:
    (recipient, token, amount, amountDuration, startTime, endTime) = entry
    if startTime <= now <= endTime or last_paid_timestamp <= endTime <= now:
      amount_per_second = amount // amountDuration

      datapoint = {
        "amount_per_second": amount_per_second,
        "from_time": max(last_paid_timestamp, startTime),
        "to_time": min(now, endTime)
      }

      if not salaries.get(recipient):
          salaries[recipient] = {}
      if salaries[recipient].get(token):
        # handle updates and deletions
        if datapoint['from_time'] < salaries[recipient][token][-1]['to_time']:
          salaries[recipient][token][-1]['to_time'] = datapoint['from_time']
        salaries[recipient][token].append(datapoint)
        
      else:
        salaries[recipient][token] = [datapoint]
        
    else:
      updated_first_paid_index += 1

  results = dict()
  for recipient in salaries.keys():
    results[recipient] = {}
    for token in salaries[recipient].keys():
      total = 0
      for entry in salaries[recipient][token]:
        total += entry['amount_per_second'] * (entry['to_time'] - entry['from_time'])
      results[recipient][token] = total

  # Write salary data to json file
  if not os.path.exists('salaries'):
    os.makedirs('salaries')
  date_now = datetime.utcfromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
  salary_json_filename = 'salaries-' + date_now + '.json'
  if test:
    salary_json_filename = 'test-' + salary_json_filename
  salary_json_filename = 'salaries/' + salary_json_filename

  with open(salary_json_filename, 'w') as salaries_dumped :
    json.dump(results, salaries_dumped, indent=4)

  # Set last paid timestamp on chain
  logger_contract.setCheckpoint(now, updated_first_paid_index, { 'from': manager })

  return salary_json_filename
