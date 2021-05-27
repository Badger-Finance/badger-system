import datetime
from enum import Enum
import json
import os
from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from scripts.systems.uniswap_system import UniswapSystem
import warnings
import requests
import brownie
import pytest
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from helpers.time_utils import days, to_days, to_timestamp, to_utc_date
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.gnosis_safe import convert_to_test_mode, exec_direct, get_first_owner
from helpers.constants import MaxUint256

console = Console()


def printUniTrade(method, params):
    path = params[2]
    input_token = path[0]
    output_token = path[-1]

    table = []
    table.append(["input token", input_token])
    table.append(["output token", output_token])
    table.append(["expected output", params[0]])
    table.append(["max input", params[1]])
    table.append(["path", params[2]])
    table.append(["recipient", params[3]])
    table.append(["expiration time", to_utc_date(params[4])])
    table.append(["time until expiration", days(params[4] - chain.time())])
    console.print(tabulate(table, headers=["metric", "value"]))


def swap_transfer(recipient, params):
    badger = connect_badger("deploy-final.json")

    badger.treasuryMultisig = connect_gnosis_safe(
        "0xD4868d98849a58F743787c77738D808376210292"
    )

    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig
    multi = GnosisSafe(badger.treasuryMultisig)

    one_wei = Wei("1")

    end_token = interface.IERC20(params["path"][-1])

    console.print("Executing Swap:", style="yellow")
    console.print(params)

    # === Approve Uniswap Router on Rewards Escrow if not approved ===
    uniswap = UniswapSystem()

    # === Approve UNI Router for Badger ===

    # Note: The allowance must first be set to 0
    id = multi.addTx(
        MultisigTxMetadata(
            description="Approve UNI Router to send BADGER",
            operation="call",
        ),
        params={
            "to": badger.token.address,
            "data": badger.token.approve.encode_input(uniswap.router, 0),
        },
    )

    tx = multi.executeTx(id)

    # Set proper allowance
    id = multi.addTx(
        MultisigTxMetadata(
            description="Approve UNI Router to send BADGER",
            operation="call",
        ),
        params={
            "to": badger.token.address,
            "data": badger.token.approve.encode_input(
                uniswap.router, int(params["max_in"] * 1.5)
            ),
        },
    )

    tx = multi.executeTx(id)

    console.print(
        {
            "rewardsEscrowBalance": val(
                badger.token.balanceOf(badger.treasuryMultisig)
            ),
            "rewardsEscrowRouterAllowance": val(
                badger.token.allowance(badger.treasuryMultisig, uniswap.router)
            ),
            "max_in": val(params["max_in"]),
        }
    )

    assert badger.token.balanceOf(badger.treasuryMultisig) > params["max_in"]
    assert (
        badger.token.allowance(badger.treasuryMultisig, uniswap.router)
        >= params["max_in"]
    )

    # === Trade Badger ===
    before = end_token.balanceOf(badger.treasuryMultisig)
    beforeBadger = badger.token.balanceOf(badger.treasuryMultisig)

    console.print({"EAO": params["exact_amount_out"]})

    expiration = chain.time() + 8000

    id = multi.addTx(
        MultisigTxMetadata(
            description="Trade Badger for output token",
            operation="call",
            callInfo={},
        ),
        params={
            "to": uniswap.router.address,
            "data": uniswap.router.swapTokensForExactTokens.encode_input(
                params["exact_amount_out"],
                int(params["max_in"] * 1.5),
                params["path"],
                badger.treasuryMultisig,
                expiration,
            ),
        },
    )

    tx = multi.executeTx(id)
    print(tx.call_trace())
    print(tx.events)

    printUniTrade(
        method="swapTokensForExactTokens",
        params=(
            params["exact_amount_out"],
            int(params["max_in"] * 1.5),
            params["path"],
            badger.treasuryMultisig,
            expiration,
        ),
    )

    console.log("=== Post Trade ===")
    console.print(
        {
            "before_input_coin": val(beforeBadger),
            "after_input_coin": val(badger.token.balanceOf(badger.treasuryMultisig)),
            "change_input_coin": val(
                beforeBadger - badger.token.balanceOf(badger.treasuryMultisig)
            ),
            "before_output_coin": val(before, decimals=end_token.decimals()),
            "post_output_coin": val(
                end_token.balanceOf(badger.treasuryMultisig),
                decimals=end_token.decimals(),
            ),
            "end_token": end_token,
            "chain_time_before": chain.time(),
        }
    )

    assert end_token.balanceOf(badger.treasuryMultisig) >= params["exact_amount_out"]
    console.print("\n[green] ✅ Actions Complete [/green]")


class SwapMode(Enum):
    EXACT_AMOUNT_IN = 0
    EXACT_AMOUNT_OUT = 1


def fetch_usd_value(token_address, amount):
    price = fetch_usd_price(address_to_id(token_address))
    return price * amount


def fetch_usd_price(token_address):
    id = address_to_id(token_address)
    url = "https://api.coingecko.com/api/v3/coins/" + id

    params = "?tickers=false&community_data=false&developer_data=false&sparkline=false"

    r = requests.get(url, params)
    data = r.json()
    usd_price = data["market_data"]["current_price"]["usd"]
    console.print(usd_price)
    return usd_price


def address_to_id(token_address):
    if token_address == registry.tokens.wbtc:
        return "wrapped-bitcoin"
    if token_address == registry.tokens.badger:
        return "badger-dao"
    if token_address == registry.tokens.usdt:
        return "usdt"
    else:
        assert False


def from_dollars(badger, token_address, dollars):
    """
    Get the amount of a given coin required for a given dollar sum at current exchange rate
    """
    # Expected output in dollars

    # Price: Output <> USD
    # Price: Input <> Output
    exchange_rate = fetch_usd_price(token_address)
    tokens_amount = dollars / exchange_rate
    decimals = interface.IERC20(token_address).decimals()
    output = int(tokens_amount * (10 ** decimals))

    console.print(
        {
            "exchange_rate": exchange_rate,
            "dollars": dollars,
            "token_amount_scaled": tokens_amount,
            "token_amount_unscaled": output,
            "decimals": decimals,
        }
    )

    return output


def main():
    """
    - Swap tokens according to parameters. Swapped tokens are returned to the swapper
    - Send test transaction to recipient. Amount is one Wei.
    - Send full transaction to recipient. Amount is specified amount minus one Wei.
    """

    badger = connect_badger("deploy-final.json")
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    multi = GnosisSafe(badger.devMultisig)

    # Parameters
    recipient = "0x08CeCe3D7e70f13afa91953Ba12b2315598ad7EA"
    dollars = 65000

    # Trade 'at max' Badger for exact amount of end coin
    max_in = from_dollars(badger, badger.token.address, dollars * 1.2)
    # exact_amount_out = from_dollars(badger, registry.tokens.wbtc, dollars)
    exact_amount_out = dollars * 10 ** 6

    params = {
        "dollars": dollars,
        "recipient": recipient,
        "token_in": badger.token.address,
        "token_out": registry.tokens.usdt,
        "swap_mode": SwapMode.EXACT_AMOUNT_OUT,
        "max_in": max_in,
        "max_in_scaled": val(max_in),
        "exact_amount_out": exact_amount_out,
        "exact_amount_out_scaled": val(exact_amount_out),
        "path": [
            badger.token.address,
            registry.tokens.wbtc,
            registry.tokens.usdc,
            registry.tokens.usdt,
        ],
    }

    console.print("===== Pre Swap =====", style="bold cyan")

    console.print(params)
    swap_transfer(recipient, params)

    console.print("===== Post Swap =====", style="bold cyan")
