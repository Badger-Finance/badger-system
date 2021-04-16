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

def __get_data__(logger_address: str, start: int, end: int) -> list:
  calls = [Call(logger_address, ['getEntry(uint256)(address,address,uint256,uint256,uint256,uint256,uint256,uint256)', i], [['recipient_'+str(i), None], ['token_'+str(i), None], ['amount_'+str(i), None], ['amountDuration_'+str(i), None], ['startTime_'+str(i), None], ['endTime_'+str(i), None], ['timestamp_'+str(i), None], ['blockNumber_'+str(i), None]]) for i in range(start, end)]
  multi = Multicall(calls)()

  return [
    (
      web3.toChecksumAddress(multi['recipient_'+str(i)]),
      web3.toChecksumAddress(multi['token_'+str(i)]),
      multi['amount_'+str(i)],
      multi['amountDuration_'+str(i)],
      multi['startTime_'+str(i)],
      multi['endTime_'+str(i)],
      multi['timestamp_'+str(i)],
      multi['blockNumber_'+str(i)]
    ) for i in range(start, end)
  ]


def fetch_salaries(logger_address: str, start_block: int, end_block: int, test=False) -> str:
  with open('build/contracts/ContributorLogger.json') as f:
    logger_abi = json.load(f)['abi']

  logger_contract = brownie.Contract.from_abi('ContributorLogger', logger_address, logger_abi)

  next_id = logger_contract.nextId()

  start_block_time = web3.eth.getBlock(start_block)['timestamp']
  end_block_time = web3.eth.getBlock(end_block)['timestamp']

  entries = __get_data__(logger_address, 0, next_id)

  salaries = dict()

  for entry in entries:
    (recipient, token, amount, amountDuration, startTime, endTime, timestamp, blockNumber) = entry
    
    if startTime <= end_block_time <= endTime or start_block_time <= endTime <= end_block_time:
      amount_per_second = amount // amountDuration

      datapoint = {
        "amount_per_second": amount_per_second,
        "from_time": max(start_block_time, startTime),
        "to_time": min(end_block_time, endTime)
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
  date_end_block_time = datetime.utcfromtimestamp(end_block_time).strftime('%Y-%m-%d %H:%M:%S')
  salary_json_filename = 'salaries-' + date_end_block_time + '.json'
  if test:
    salary_json_filename = 'test-' + salary_json_filename
  salary_json_filename = 'salaries/' + salary_json_filename

  with open(salary_json_filename, 'w') as salaries_dumped :
    json.dump(results, salaries_dumped, indent=4)

  return salary_json_filename
