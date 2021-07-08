from tabulate import tabulate
from helpers.utils import (
    fragments_to_shares,
    initial_fragments_to_current_fragments,
    shares_to_fragments,
    to_digg_shares,
    val,
)
from helpers.token_utils import (
    BalanceSnapshotter,
    token_metadata,
    asset_to_address,
    to_token_scale,
)
from helpers.ltcc.LtccRecipient import LtccRecipient
import csv


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
    payments = LtccPayments("Payments")
    with open(filepath, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter="\t", quotechar="|")
        for row in reader:
            print(row[0], row[1], row[2], row[3])
            payments.add_recipient(row[1], row[0], {"usdc": row[2], "badger": row[3]})
    return payments
