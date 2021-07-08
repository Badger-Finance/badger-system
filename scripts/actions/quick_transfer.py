from enum import Enum

import requests
from brownie import Wei, accounts, interface, rpc
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from helpers.registry import registry
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.uniswap_system import UniswapSystem
from helpers.gas_utils import gas_strategies

console = Console()
gas_strategies.set_default(gas_strategies.exponentialScalingFast)


def main():
    badger = connect_badger(load_deployer=True)
    badger.deployer.transfer(
        "0x5FcF1e5be48D2CB5F0B06e83C2B000049EaF7636", amount=Wei("1 ether")
    )
