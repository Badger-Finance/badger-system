import datetime
from enum import Enum
import json
import os
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

    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig
    multi = GnosisSafe(badger.devMultisig)

    one_wei = Wei("1")

    end_token = interface.IERC20(params["path"][-1])

    console.print("Executing Swap:", style="yellow")
    console.print(params)

    # === Approve Uniswap Router on Rewards Escrow if not approved ===
    uniswap = UniswapSystem()
    assert badger.rewardsEscrow.isApproved(badger.token)
    assert badger.rewardsEscrow.isApproved(uniswap.router)

    # === Approve UNI Router for Badger ===

    # Note: The allowance must first be set to 0
    id = multi.addTx(
        MultisigTxMetadata(
            description="Approve UNI Router to send BADGER",
            operation="call",
            callInfo={"address": uniswap.router, "amount": params["max_in"] // 2},
        ),
        params={
            "to": badger.rewardsEscrow.address,
            "data": badger.rewardsEscrow.call.encode_input(
                badger.token,
                0,
                badger.token.approve.encode_input(uniswap.router, 0),
            ),
        },
    )

    tx = multi.executeTx(id)

    # Set proper allowance
    id = multi.addTx(
        MultisigTxMetadata(
            description="Approve UNI Router to send BADGER",
            operation="call",
            callInfo={"address": uniswap.router, "amount": params["max_in"] // 2},
        ),
        params={
            "to": badger.rewardsEscrow.address,
            "data": badger.rewardsEscrow.call.encode_input(
                badger.token,
                0,
                badger.token.approve.encode_input(uniswap.router, params["max_in"]),
            ),
        },
    )

    tx = multi.executeTx(id)

    console.print(
        {
            "rewardsEscrowBalance": val(badger.token.balanceOf(badger.rewardsEscrow)),
            "rewardsEscrowRouterAllowance": val(
                badger.token.allowance(badger.rewardsEscrow, uniswap.router)
            ),
            "max_in": val(params["max_in"]),
        }
    )

    assert badger.token.balanceOf(badger.rewardsEscrow) > params["max_in"]
    assert (
        badger.token.allowance(badger.rewardsEscrow, uniswap.router) >= params["max_in"]
    )

    # === Trade Badger for USDC through WBTC ===
    before = end_token.balanceOf(badger.rewardsEscrow)
    beforeBadger = badger.token.balanceOf(badger.rewardsEscrow)

    console.print({"EAO": params["exact_amount_out"]})

    expiration = chain.time() + 8000

    id = multi.addTx(
        MultisigTxMetadata(
            description="Trade Badger for output token",
            operation="call",
            callInfo={},
        ),
        params={
            "to": badger.rewardsEscrow.address,
            "data": badger.rewardsEscrow.call.encode_input(
                uniswap.router,
                0,
                uniswap.router.swapTokensForExactTokens.encode_input(
                    params["exact_amount_out"],
                    MaxUint256,
                    params["path"],
                    badger.rewardsEscrow,
                    expiration,
                ),
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
            params["max_in"],
            params["path"],
            badger.rewardsEscrow,
            expiration,
        ),
    )

    console.log("=== Post Trade ===")
    console.print(
        {
            "before_input_coin": beforeBadger,
            "after_input_coin": badger.token.balanceOf(badger.rewardsEscrow),
            "before_output_coin": before,
            "post_output_coin": end_token.balanceOf(badger.rewardsEscrow),
            "end_token": end_token,
            "chain_time_before": chain.time(),
        }
    )

    assert end_token.balanceOf(badger.rewardsEscrow) >= params["exact_amount_out"]

    # === Approve Recipient if not approved ===
    if not badger.rewardsEscrow.isApproved(recipient):
        id = multi.addTx(
            MultisigTxMetadata(
                description="Approve the transfer recipient",
                operation="approveRecipient",
                callInfo={},
            ),
            params={
                "to": badger.rewardsEscrow.address,
                "data": badger.rewardsEscrow.approveRecipient.encode_input(recipient),
            },
        )

        multi.executeTx(id)

    assert badger.rewardsEscrow.isApproved(recipient)

    # === Test Payment to recipient ===
    before = end_token.balanceOf(recipient)

    id = multi.addTx(
        MultisigTxMetadata(
            description="Test payment to recipientt",
            operation="transfer",
            callInfo={"to": recipient, "amount": one_wei},
        ),
        params={
            "to": badger.rewardsEscrow.address,
            "data": badger.rewardsEscrow.transfer.encode_input(
                end_token, recipient, one_wei
            ),
        },
    )

    multi.executeTx(id)
    after = end_token.balanceOf(recipient)
    assert after == before + one_wei

    # === Full Payment to recipient ===
    rest = params["exact_amount_out"] - 1
    before = end_token.balanceOf(recipient)

    id = multi.addTx(
        MultisigTxMetadata(
            description="$12k payment to auditor, in USDC",
            operation="transfer",
            callInfo={"to": recipient, "amount": rest},
        ),
        params={
            "to": badger.rewardsEscrow.address,
            "data": badger.rewardsEscrow.transfer.encode_input(
                end_token, recipient, rest
            ),
        },
    )

    multi.executeTx(id)

    after = end_token.balanceOf(recipient)

    assert after == before + rest

    print(before, after, before + params["exact_amount_out"])

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
    if token_address == registry.tokens.digg:
        return "digg"
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
    dollars = 10100

    # Trade 'at max' Badger for exact amount of end coin
    max_in = from_dollars(badger, badger.token.address, dollars * 1.2)
    exact_amount_out = from_dollars(badger, registry.tokens.wbtc, dollars)

    params = {
        "dollars": dollars,
        "recipient": recipient,
        "token_in": badger.token.address,
        "token_out": registry.tokens.wbtc,
        "swap_mode": SwapMode.EXACT_AMOUNT_OUT,
        "max_in": max_in,
        "max_in_scaled": val(max_in),
        "exact_amount_out": exact_amount_out,
        "exact_amount_out_scaled": val(exact_amount_out),
        "path": [badger.token.address, registry.tokens.wbtc],
    }

    console.print("===== Pre Swap =====", style="bold cyan")

    console.print(params)
    swap_transfer(recipient, params)

    console.print("===== Post Swap =====", style="bold cyan")
