from enum import Enum
from helpers.token_utils import BalanceSnapshotter
from ape_safe import ApeSafe

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

console = Console()


def main():
    """
    AAVE
    Compoound
    y3Crv
    """

    badger = connect_badger()
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    dev = badger.deployer

    # AAVE
    aave = registry.aave_system()
    tokens = registry.token_system()
    usdc = tokens.erc20_by_key("usdc")

    safe = ApeSafe(badger.devMultisig)

    # TODO: Track the balances of the tokens representing your position here: AAVE USDC (aUSDC), Compound USDC (cUSDC), y3Crv Vault Position (y3Crv)

    # TODO: Figure out the addresses of these derived tokens

    # TODO: Track the balances of all the appropriate contracts where the USDC ends up
    snap = BalanceSnapshotter([usdc], [badger.devMultisig])

    usdc_per_position = Wei("3237154.58 szabo")  # szabo = 10^6

    # AAVE Deposit
    usdc.approve(usdc_per_position, aave.lendingPool, {"from": dev})
    aave.deposit(usdc, usdc_per_position, {"from": dev})

    # Compound Deposit

    """
    y3Crv
    Stake in CRV (one asset only> What is the slippage here vs otherwise.)
    Approve
    Depsoit into Yearn vaukt
    """

    # Testing: Check balances and assert we have the aToken

    # TODO: Safety features. Call a custom contract balanceVerifier that verifies that the multisig owns the appropriate amount of coins from each platform
