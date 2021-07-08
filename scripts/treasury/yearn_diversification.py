from enum import Enum
from helpers.token_utils import BalanceSnapshotter
from ape_safe import ApeSafe

import requests
from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper, GnosisSafe, MultisigTxMetadata
from helpers.registry import registry
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.uniswap_system import UniswapSystem

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
    helper = ApeSafeHelper(badger, safe)

    # Fetch tokens for snap + interactions
    usdc = safe.contract("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
    dai = safe.contract("0x6B175474E89094C44Da98b954EedeAC495271d0F")
    yDai = safe.contract("0x19D3364A399d251E894aC732651be8B0E4e85001")
    yUsdc = safe.contract("0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9")

    usdc_to_deposit = "1500000000000"
    usdc_to_swap = "1500000000000"  ## 1.5 * 10^6 (Million) * 10^6 (Decimals)

    # TODO: Track the balances of the tokens representing your position here: AAVE USDC (aUSDC), Compound USDC (cUSDC), y3Crv Vault Position (y3Crv)
    snap = BalanceSnapshotter([usdc, dai, yDai, yUsdc], [badger.devMultisig,],)
    snap.snap()

    current_dai_balance = dai.balanceOf(badger.devMultisig.address)

    ## NOTE: Swap to DAI with Curve
    ## Coins[0] == DAI
    ## Coins[1] == UDC
    curve_pool = safe.contract("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7")
    dai_out = curve_pool.get_dy(1, 0, usdc_to_swap)

    with_slippage = dai_out * 0.99
    print("With slippage")
    print(with_slippage)

    usdc.approve(curve_pool.address, usdc_to_swap)
    curve_pool.exchange(1, 0, usdc_to_swap, with_slippage)

    post_swap_balance = dai.balanceOf(badger.devMultisig.address)
    dai_to_deposit = post_swap_balance - current_dai_balance
    print("dai_to_deposit")
    print(dai_to_deposit)

    snap.snap()
    snap.diff_last_two()

    ## NOTE: Deposit DAI to Yearn
    ## TODO: Get balance of DAI to determine how to deposit
    yDaiVault = helper.contract_from_abi(
        "0x19D3364A399d251E894aC732651be8B0E4e85001",
        "yDaiVault",
        interface.VaultAPI.abi,
    )
    dai.approve(yDaiVault.address, dai_to_deposit)
    yDaiVault.deposit(dai_to_deposit)

    snap.snap()
    snap.diff_last_two()

    ## NOTE: Deposit USDC to Yearn
    yUsdcVault = helper.contract_from_abi(
        "0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9",
        "yUsdcVault",
        iinterface.VaultAPI.abi,
    )

    usdc.approve(yUsdcVault.address, usdc_to_deposit)
    yUsdcVault.deposit(usdc_deposit_amount)

    ## DONE

    snap.snap()
    snap.diff_last_two()

    ## Publish all Txs
    helper.publish()
