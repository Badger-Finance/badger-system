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

CHECKPOINT_PATH = 'checkpoint/salary.json'
CHECKPOINT_FOLDER = CHECKPOINT_PATH.split('/')[0]


def __get_data__(logger_address: str, start: int, end: int) -> list:
  calls = [Call(logger_address, ['getEntry(uint256)(uint256,address,address,uint128,uint40,uint40)', i], [['id_'+str(i), None], ['recipient_'+str(i), None], ['token_'+str(i), None], ['amountPerSecond_'+str(i), None], ['startTime_'+str(i), None], ['endTime_'+str(i), None]]) for i in range(start, end)]
  multi = Multicall(calls)()

  return [
    (
      multi['id_'+str(i)],
      web3.toChecksumAddress(multi['recipient_'+str(i)]),
      web3.toChecksumAddress(multi['token_'+str(i)]),
      multi['amountPerSecond_'+str(i)],
      multi['startTime_'+str(i)],
      multi['endTime_'+str(i)]
    ) for i in range(start, end)
  ]


def __get_checkpoint__():
  if os.path.exists(CHECKPOINT_PATH):
    with open(CHECKPOINT_PATH) as f:
      return json.load(f)['start_index']
  return 0


def __write_checkpoint__(start_index: int):
  if not os.path.exists(CHECKPOINT_FOLDER):
    os.makedirs(CHECKPOINT_FOLDER)
  with open(CHECKPOINT_PATH, 'w') as f :
    json.dump({ 'start_index': start_index }, f, indent=4)


def fetch_salaries(logger_address: str, start_block: int, end_block: int, test=False) -> str:
  with open('build/contracts/ContributorLogger.json') as f:
    logger_abi = json.load(f)['abi']
  
  start_index = __get_checkpoint__()
  updating_checkpoint = True # increment the checkpointed start_index until an entry is found in range

  logger_contract = brownie.Contract.from_abi('ContributorLogger', logger_address, logger_abi)

  next_id = logger_contract.nextId()

  start_block_time = web3.eth.getBlock(start_block)['timestamp']
  end_block_time = web3.eth.getBlock(end_block)['timestamp']

  entries = __get_data__(logger_address, start_index, next_id)
  entries.sort(key=lambda e: e[3]) # sort by startTime

  salaries = dict()

  for entry in entries:
    (id, recipient, token, amountPerSecond, startTime, endTime) = entry

    if startTime <= end_block_time and endTime > start_block_time:
      updating_checkpoint = False

      datapoint = {
        "id": id,
        "amount_per_second": amountPerSecond,
        "from_time": max(start_block_time, startTime),
        "to_time": min(end_block_time, endTime)
      }

      if not salaries.get(recipient):
          salaries[recipient] = dict()
      if salaries[recipient].get(token):
        # handle updates and deletions
        if datapoint['from_time'] < salaries[recipient][token][-1]['to_time']:
          # more recently added entries take precedent when there's an overlap
          if datapoint['id'] > salaries[recipient][token][-1]['id']:
            salaries[recipient][token][-1]['to_time'] = datapoint['from_time']
          else:
            datapoint['from_time'] = salaries[recipient][token][-1]['to_time']
        salaries[recipient][token].append(datapoint)
        
      else:
        salaries[recipient][token] = [datapoint]

    elif updating_checkpoint:
      start_index += 1

  results = dict()
  for recipient, tokens in salaries.items():
    results[recipient] = dict()
    for token in tokens:
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

  # Write start_index to checkpoint
  __write_checkpoint__(start_index)

  return salary_json_filename
