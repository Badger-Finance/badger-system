from typing import Iterable
from helpers.token_utils import (
    BalanceSnapshotter,
    token_metadata,
    asset_to_address,
    to_token_scale,
)
from ape_safe import ApeSafe
from helpers.coingecko import fetch_usd_price, fetch_usd_price_eth
import csv

from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from helpers.constants import *
from helpers.gnosis_safe import (
    GnosisSafe,
    MultisigTx,
    MultisigTxMetadata,
    convert_to_test_mode,
    exec_direct,
    get_first_owner,
)
from helpers.registry import registry
from helpers.time_utils import days, hours, to_days, to_timestamp, to_utc_date
from helpers.utils import (
    fragments_to_shares,
    initial_fragments_to_current_fragments,
    shares_to_fragments,
    to_digg_shares,
    val,
)
from rich import pretty
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

console = Console()
pretty.install()


class LtccRecipient:
    def __init__(self, name, address, assets):
        self.name = name
        self.address = address
        self.assets = {}

        for key, value in assets.items():
            # Scale token values with appropriate decimals for that token
            scaled_value = to_token_scale(key, value)
            self.assets[key] = scaled_value
            console.print(key, self.assets[key])

    def get_amount(self, asset):
        console.print(asset, self.assets)
        if asset in self.assets:
            return self.assets[asset]
        else:
            return -1


class LtccPayments:
    def __init__(self, date_range):
        self.date_range = date_range
        self.recipients = []

    def add_recipient(self, name, address, assets):
        self.recipients.append(LtccRecipient(name, address, assets))

    def print_recipients(self):
        table = []
        for recipient in self.recipients:
            table.append(
                [
                    recipient.name,
                    recipient.address,
                    val(
                        recipient.get_amount("usdc"),
                        decimals=token_metadata.get_decimals(asset_to_address("usdc")),
                    ),
                    val(
                        recipient.get_amount("badger"),
                        decimals=token_metadata.get_decimals(
                            asset_to_address("badger")
                        ),
                    ),
                ]
            )
        print("===== LTCC Payments for {} =====".format(self.date_range))
        print(tabulate(table, headers=["name", "address", "usdc", "badger"]))


def load_ltcc_recipients(filepath):
    payments = LtccPayments("3/15 - 3/31")
    with open(filepath, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter="\t", quotechar="|")
        for row in reader:
            print(", ".join(row))
            payments.add_recipient(row[0], row[1], {"usdc": row[2], "badger": row[3]})
    return payments


def main():
    badger = connect_badger()
    multisig = badger.devMultisig

    safe = ApeSafe(multisig.address)

    payments = load_ltcc_recipients("scripts/actions/treasury/ltcc_recipients.csv")
    payments.print_recipients()

    usdcToken = safe.contract_from_abi(registry.tokens.usdc, "IERC20", interface.IERC20.abi)
    badgerToken = safe.contract(badger.token.address)

    snap = BalanceSnapshotter(
        [badgerToken, usdcToken], [multisig, badger.deployer, badger.rewardsEscrow]
    )

    for recipient in payments.recipients:
        snap.add_account(recipient.address)

    snap.snap(name="Before Transfers", print=True)

    for recipient in payments.recipients:
        console.print(recipient.get_amount("usdc"), recipient.get_amount("badger"))
        usdcToken.transfer(recipient.address, recipient.get_amount("usdc"))
        badgerToken.transfer(recipient.address, recipient.get_amount("badger"))

    snap.snap(name="After Transfers")
    snap.diff_last_two()

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx)
    data = safe.print_transaction(safe_tx)
    safe.post_transaction(safe_tx)

