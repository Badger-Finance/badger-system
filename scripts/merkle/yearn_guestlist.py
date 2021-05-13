from helpers.merkle_tree import MerkleTree
import json
from brownie import *
from config.keeper import keeper_config
from eth_abi import encode_abi
from eth_utils.hexadecimal import encode_hex
from helpers.console_utils import console
from helpers.gas_utils import gas_strategies
from helpers.registry import registry
from helpers.sett.SnapshotManager import SnapshotManager
from helpers.utils import tx_wait, val
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate


def encode_nodes(accounts):
    encoded_accounts = []
    for index in range(0, len(accounts)):
        data = accounts[index]
        encoded = encode_hex(
            encode_abi(
                ["uint256", "address", "uint256"],
                (index, data["account"], data["score"]),
            )
        )
        encoded_accounts.append(encoded)
    return encoded_accounts


def parse_accounts(data):
    output = []
    for key, score in data.items():
        encoded = {}
        encoded["account"] = key
        encoded["score"] = score
        output.append(encoded)
    return output


def main():
    with open("merkle/badger_scores.json") as f:
        accounts = json.load(f)

    accounts = parse_accounts(accounts)

    encoded_accounts = encode_nodes(accounts)
    tree = MerkleTree(encoded_accounts)

    output = {"root": encode_hex(tree.root), "claims": {}}

    for index in range(0, len(accounts)):
        data = accounts[index]
        node = encoded_accounts[index]

        output["claims"][data["account"]] = {
            "account": data["account"],
            "score": data["score"],
            "proof": tree.get_proof(index),
            "node": node,
        }

    with open("merkle/yearn_merklelist.json", "w") as f:
        json.dump(output, f, indent=4)
