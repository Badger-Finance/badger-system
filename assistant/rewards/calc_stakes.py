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
from helpers.constants import ZERO_ADDRESS


def calc_geyser_stakes(geyser, globalStartBlock, snapshotStartBlock, periodEndBlock):
    print("geyser initial snapshot for " + geyser.address)
    pre_actions = collect_actions(geyser, globalStartBlock, snapshotStartBlock - 1)
    pre_snapshot = process_snapshot(
        pre_actions, globalStartBlock, snapshotStartBlock - 1
    )

    # Construct stakingWeight (rather than just stakingShareSeconds), with values modified by _average_ multiplier for stakes within a periods
    actions = collect_actions(geyser, snapshotStartBlock, periodEndBlock)
    stake_weights = calculate_stake_weights(pre_snapshot, actions)
    print(stake_weights)
    return stake_weights


def events_to_stakes(geyser, startBlock, snapshotBlock):
    """
    Get the current stakes of a user at a given snapshot block
    user -> stake[]
    stake:{amount, stakedAt}
    """
    stakes = DotMap()
    contract = web3.eth.contract(geyser.address, abi=BadgerGeyser.abi)
    for start in trange(startBlock, snapshotBlock, 1000):
        end = min(start + 999, snapshotBlock)
        logs = contract.events.Staked().getLogs(fromBlock=start, toBlock=end)
        for log in logs:
            user = log["args"]["user"]
            if user != ZERO_ADDRESS:
                if not stakes[user]:
                    stakes[user] = []
                stakes[user].push(
                    {
                        "amount": log["args"]["amount"],
                        "stakedAt": log["args"]["timestamp"],
                    }
                )

    return stakes


def collect_actions(geyser, startBlock, endBlock):
    """
    Construct a sequence of stake and unstake actions from events
    Unstakes for a given block are ALWAYS processed after the stakes, as we aren't tracking the transaction order within a block
    This could have extremely minor impact on rewards if stakes & unstakes happen during the same block (it would break if tracked the other way around, without knowing order)
    user -> timestamp -> action[]
    action: STAKE or UNSTAKE w/ parameters. (Stakes are always processed before unstakes within a given block)
    """
    contract = web3.eth.contract(geyser.address, abi=BadgerGeyser.abi)
    actions = DotMap()

    # Add stake actions
    for start in trange(startBlock, endBlock, 1000):
        end = min(start + 999, endBlock)
        logs = contract.events.Staked().getLogs(fromBlock=start, toBlock=end)
        for log in logs:
            timestamp = log["args"]["timestamp"]
            user = log["args"]["args"]

            if user != ZERO_ADDRESS:
                if not actions[user][timestamp]:
                    actions[user][timestamp] = []
                actions[user][timestamp].push(
                    {
                        "action": "STAKE",
                        "amount": log["args"]["amount"],
                        "stakedAt": log["args"]["timestamp"],
                    }
                )

    # Add unstake actions
    for start in trange(startBlock, endBlock, 1000):
        end = min(start + 999, endBlock)
        logs = contract.events.Unstaked().getLogs(fromBlock=start, toBlock=end)
        for log in logs:
            timestamp = log["args"]["timestamp"]
            user = log["args"]["args"]

            if user != ZERO_ADDRESS:
                if not actions[user][timestamp]:
                    actions[user][timestamp] = []
                actions[user][timestamp].push(
                    {
                        "action": "UNSTAKE",
                        "amount": log["args"]["amount"],
                        "timestamp": log["args"]["timestamp"],
                    }
                )

    return actions


def process_snapshot(actions, startBlock, endBlock):
    """
    Add stakes
    Remove stakes according to unstaking rules (LIFO)
    """
    for action in actions.values():
        print(action)


def calculate_stake_weights(stakes, actions):
    """
    Add stakes
    Remove stakes according to unstaking rules (LIFO)
    Calculate the "stake weight" of each user
    user -> stakeWeight
    """
    for action in actions.values():
        print(action)


def ensure_archive_node():
    fresh = web3.eth.call({"to": str(EMN), "data": EMN.totalSupply.encode_input()})
    old = web3.eth.call(
        {"to": str(EMN), "data": EMN.totalSupply.encode_input()}, SNAPSHOT_BLOCK
    )
    assert fresh != old, "this step requires an archive node"
