

import json
import os
import warnings

from brownie import *
from config.badger_config import badger_config
from config.ethereum import eth_config
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

from helpers.registry import registry
from helpers.time_utils import daysToSeconds, hours

console = Console()


def get_account(account):
    if account == "deployer":
        with open("badger_deployer_keystore.json") as keyfile:
            encrypted_key = keyfile.read()
            private_key = web3.eth.account.decrypt(encrypted_key, "-")
            return private_key
    if account == "keeper":
        with open("badger_keeper_keystore.json") as keyfile:
            encrypted_key = keyfile.read()
            private_key = web3.eth.account.decrypt(encrypted_key, "-")
            return private_key
    if account == "guardian":
        with open("badger_guardian_keystore.json") as keyfile:
            encrypted_key = keyfile.read()
            private_key = web3.eth.account.decrypt(encrypted_key, "-")
            return private_key

def get_account_address(account):
    if account == "deployer":
        return "0xDA25ee226E534d868f0Dd8a459536b03fEE9079b"
    if account == "keeper":
        return "0x872213E29C85d7e30F1C8202FC47eD1Ec124BB1D"
    if account == "guardian":
        return "0x29F7F8896Fb913CF7f9949C623F896a154727919"


def send(to, data, deployer):
    key = get_account(deployer)
    keyAddress = get_account_address(deployer)

    transaction = {
        "to": to.address,
        "value": 0,
        "gas": 2000000,
        "gasPrice": eth_config.fetch_gas_price(),
        "nonce": web3.eth.getTransactionCount(keyAddress),
        "chainId": 1,
        "data": data,
    }

    signed = web3.eth.account.sign_transaction(transaction, key)
    tx_hash = web3.eth.sendRawTransaction(signed.rawTransaction)

    print("Sent: ", str(tx_hash))

    tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)
    print("Confirmed: ", str(tx_hash))
    print(tx_receipt['gasUsed'], "gasUsed")
