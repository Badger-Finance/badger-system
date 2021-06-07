from enum import Enum
from helpers.token_utils import BalanceSnapshotter
from ape_safe import ApeSafe

import requests
from brownie import Wei, accounts, interface, rpc
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper, GnosisSafe, MultisigTxMetadata
from helpers.registry import registry
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.uniswap_system import UniswapSystem
import time

console = Console()


def main():
    """
    First, swap half of the USDC into DAI
    Deposit USDC portion in to Yearn USDC Vault V2
    Deposit DAI portion in to Yearn DAI Vault V2
    For the deposits, create small test transactions first
    """

    badger = connect_badger()
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    safe = ApeSafe(badger.devMultisig.address)

    # Fetch tokens for snap + interactions


    print("safe")
    ## TODO: Does this work?
    usdc = safe.contract("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
    dai = safe.contract("0x6B175474E89094C44Da98b954EedeAC495271d0F")
    yDai = safe.contract("0x19D3364A399d251E894aC732651be8B0E4e85001")
    yUsdc = safe.contract("0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9")

    usdc_to_swap = "1500000000000"  ## 1.5 * 10^6 (Million) * 10^6 (Decimals)
    dai_min = "1497630000000000000000000"  ## 1497630 * 10^18 (decimals)

    # TODO: Track the balances of the tokens representing your position here: AAVE USDC (aUSDC), Compound USDC (cUSDC), y3Crv Vault Position (y3Crv)
    snap = BalanceSnapshotter(
        [usdc, dai, yDai, yUsdc],
        [
            badger.devMultisig,
        ],
    )
    snap.snap()

    ## NOTE: Swap to DAI
    uniswap_router = safe.contract("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
    usdc.approve(uniswap_router, usdc_to_swap)
    uniswap_router.swapExactTokensForTokens(
        usdc_to_swap,
        dai_min,
        [usdc.address, dai.address],
        badger.devMultisig.address,
        time.time() + 500, ## Give it 500 secs
    )

    snap.snap()
    snap.diff_last_two()

    ## NOTE: Deposit DAI to Yearn
    ## TODO: Get balance of DAI to determine how to deposit
    yDai = safe.contract("0x19D3364A399d251E894aC732651be8B0E4e85001")

    dai_deposit_amount = "1497630000000000000000000"  ## TODO, do proper
    dai.approve(yDai.address, dai_deposit_amount)
    yDai.deposit(dai_deposit_amount)

    snap.snap()
    snap.diff_last_two()

    ## NOTE: Deposit USDC to Yearn
    yUsdc = safe.contract("0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9")

    usdc_deposit_amount = "1500000000000"
    usdc.approve(yUsdc.address, usdc_deposit_amount)
    yUsdc.deposit(usdc_deposit_amount)

    ## DONE

    snap.snap()
    snap.diff_last_two()


    helper = ApeSafeHelper(badger, safe)
    helper.publish()
