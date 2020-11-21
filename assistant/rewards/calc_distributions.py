import json
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from functools import partial, wraps
from itertools import zip_longest
from pathlib import Path
from dotmap import DotMap
import toml
from brownie import MerkleDistributor, Wei, accounts, interface, rpc, web3
from eth_abi import decode_single, encode_single
from eth_abi.packed import encode_abi_packed
from eth_utils import encode_hex
from toolz import valfilter, valmap
from tqdm import tqdm, trange
from click import secho
from helpers.constants import *

"""
Determine how much of each token is distributed within the specified block window
    - Get the tokens for the geyser
    - Read the unlock schedules for each token
        - For each schedule, determine how many tokens should be distributed during the window
        - Sum the schedule amounts for an overall distribution for the token

token -> amount
"""

def calc_geyser_distributions(geyser, startBlock, endBlock):
    startTime = web3.eth.getBlock(startBlock)
    endTime = web3.eth.getBlock(endBlock)

    print("blocks between", startTime, endTime)
    
    distributions = DotMap()

    tokens = geyser.getDistributionTokens()
    print(tokens)
    for token in tokens:
        amount = 0
        schedules = geyser.getUnlockSchedules(token)
        print(schedules)
        for schedule in schedules:
            schedule


def add_allocations(current, geyserDistributions):
    """
    All the allocation map to an existing map
    """
    assert False
