from dotmap import DotMap
from helpers.proxy_utils import deploy_proxy
from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from helpers.time_utils import days, hours
import os
import json
from scripts.systems.badger_system import connect_badger
import warnings
from tabulate import tabulate
from brownie import *
from helpers.registry import registry
from rich.console import Console
from config.badger_config import badger_config

console = Console()


def main():
    badger = connect_badger(badger_config.prod_json)
    deployer = badger.deployer
    # distribute_from_whales(deployer)

    # Deploy Honeypot
    honeypotLogic = HoneypotMeme.deploy({"from": deployer})

    honeypot_params = DotMap(
        token=badger.token,
        amount=Wei("2500 ether"),
        nftIndicies=[97, 98, 99, 100, 101, 102],
        meme="0xe4605d46Fd0B3f8329d936a8b258D69276cBa264",
        badgerCollection="0x14dC10FA6E4878280F9CA0D9f32dDAEa8C7d4d45",
    )

    honeypot = deploy_proxy(
        "HoneypotMeme",
        HoneypotMeme.abi,
        honeypotLogic.address,
        badger.devProxyAdmin.address,
        honeypotLogic.initialize.encode_input(
            honeypot_params.token,
            honeypot_params.amount,
            honeypot_params.nftIndicies,
        ),
        deployer,
    )

    assert honeypot.token() == badger.token
    assert honeypot.memeLtd() == honeypot_params.meme
    assert honeypot.honeypot() == honeypot_params.amount
    assert honeypot.nftIndicies(0) == honeypot_params.nftIndicies[0]
    assert honeypot.nftIndicies(1) == honeypot_params.nftIndicies[1]
    assert honeypot.nftIndicies(2) == honeypot_params.nftIndicies[2]
    assert honeypot.nftIndicies(3) == honeypot_params.nftIndicies[3]
    assert honeypot.nftIndicies(4) == honeypot_params.nftIndicies[4]
    assert honeypot.nftIndicies(5) == honeypot_params.nftIndicies[5]
