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

console = Console()


def transfer_badger(recipient, params):
    badger = connect_badger("deploy-final.json")

    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig
    multi = GnosisSafe(badger.devMultisig)

    one_wei = Wei("1")
    end_token = badger.token

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
    if params["use_test_payment"]:
        id = multi.addTx(
            MultisigTxMetadata(
                description="Test payment: {} badger to {}".format(one_wei, recipient),
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
    rest = 0
    if params["use_test_payment"]:
        rest = params["amount"] - 1
    else:
        rest = params["amount"]

    before = end_token.balanceOf(recipient)

    id = multi.addTx(
        MultisigTxMetadata(
            description="Full payment, {} badger to {}".format(val(rest), recipient),
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

    print(before, after, before + params["amount"])

    console.print("\n[green] ✅ Actions Complete [/green]")


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
    Transfer badger to recipient, ensuring they are approved as recipient first
    Use test tx, full tx model
    Can convert from dollar value
    """

    badger = connect_badger("deploy-final.json")
    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert badger.devMultisig == expectedMultisig

    multi = GnosisSafe(badger.devMultisig)

    # Parameters
    recipient = "0xD73b03F1Ea390fEB20D879e4DFb83F1245C8D4be"
    dollars = 45000

    # amount = from_dollars(badger, badger.token.address, dollars)
    amount = Wei("45000 ether")

    params = {
        "dollars": dollars,
        "recipient": recipient,
        "amount": amount,
        "amount_scaled": val(amount),
        "use_test_payment": True,
    }

    console.print("===== Pre Transfer =====", style="bold cyan")

    console.print(params)
    transfer_badger(recipient, params)

    console.print("===== Post Transfer =====", style="bold cyan")
