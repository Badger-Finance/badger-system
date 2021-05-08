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
        self.totals = {"usdc": 0, "badger": 0}

    def add_recipient(self, address, name, assets):
        self.recipients.append(LtccRecipient(name, address, assets))

    def calc_totals(self):
        totals = {"usdc": 0, "badger": 0}
        for recipient in self.recipients:
            totals["usdc"] += recipient.get_amount("usdc")
            totals["badger"] += recipient.get_amount("badger")
        self.totals = totals

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
        table.append(
            [
                "Totals",
                "-",
                val(
                    self.totals["usdc"],
                    decimals=token_metadata.get_decimals(asset_to_address("usdc")),
                ),
                val(
                    self.totals["badger"],
                    decimals=token_metadata.get_decimals(asset_to_address("badger")),
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
            print(row[0], row[1], row[2], row[3])
            payments.add_recipient(row[0], row[1], {"usdc": row[2], "badger": row[3]})
    return payments


def badger_to_bBadger(badger, amount):
    bBadger = badger.getSett("native.badger")
    ppfs = bBadger.getPricePerFullShare()

    console.print(
        {
            "badger amount": amount,
            "ppfs": ppfs,
            "mult": 10 ** badger.token.decimals(),
            "bBadger amount": amount * 10 ** badger.token.decimals() // ppfs,
        }
    )

    return amount * 10 ** badger.token.decimals() // ppfs


def main():
    badger = connect_badger()
    multisig = badger.treasuryMultisig

    safe = ApeSafe(multisig.address)

    payments = load_ltcc_recipients("scripts/actions/treasury/ltcc_recipients.csv")
    payments.calc_totals()
    payments.print_recipients()

    abi = Sett.abi
    bBadger = safe.contract_from_abi(
        badger.getSett("native.badger").address, "Sett", abi
    )

    usdcToken = safe.contract_from_abi(
        registry.tokens.usdc, "IERC20", interface.IERC20.abi
    )
    badgerToken = safe.contract_from_abi(
        badger.token.address, "IERC20", interface.IERC20.abi
    )

    # TODO: Do this in bBadger going forward - this is the way.
    # Approve treasury multi to stake
    # Deposit badger -> bBadger

    snap = BalanceSnapshotter(
        [badgerToken, bBadger, usdcToken],
        [multisig, badger.deployer, badger.rewardsEscrow],
    )

    for recipient in payments.recipients:
        snap.add_account(recipient.address)

    snap.snap(name="Before bBadger Deposit")

    # assert bBadger.approved(multisig)
    # badger_total = payments.totals["badger"]
    # assert badgerToken.balanceOf(multisig.address) >= badger_total
    # bBadger_total = badger_to_bBadger(badger, badger_total)
    # badgerToken.approve(bBadger, badger_total)

    # assert badgerToken.allowance(multisig.address, bBadger.address) >= badger_total
    # bBadger.deposit(badger_total)

    # snap.snap(name="Before Transfers")
    # snap.diff_last_two()

    for recipient in payments.recipients:
        bBadger_amount = badger_to_bBadger(badger, recipient.get_amount("badger"))
        console.print(recipient.address, recipient.get_amount("badger"), bBadger_amount)
        diff = bBadger_amount - bBadger.balanceOf(multisig)

        console.print(bBadger.balanceOf(multisig), diff)

        if bBadger.balanceOf(multisig) < bBadger_amount:
            assert diff < Wei("0.1 ether")
            bBadger_amount = bBadger.balanceOf(multisig)

        tx = usdcToken.transfer(recipient.address, recipient.get_amount("usdc"))
        tx = bBadger.transfer(recipient.address, bBadger_amount)

    snap.snap(name="After Transfers")
    snap.diff_last_two()

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx)
    data = safe.print_transaction(safe_tx)
    safe.post_transaction(safe_tx)
