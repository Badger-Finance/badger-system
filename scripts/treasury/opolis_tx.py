from typing import Iterable
from helpers.token_utils import (
    BalanceSnapshotter,
    token_metadata,
    asset_to_address,
    to_token_scale,
    badger_to_bBadger
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
from helpers.ltcc import LtccPayments, LtccRecipient, load_ltcc_recipients
console = Console()
pretty.install()

def main():
    badger = connect_badger()
    multisig = badger.treasuryMultisig

    safe = ApeSafe(multisig.address)

    payments = load_ltcc_recipients("data/ltcc_recipients.csv")
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

    opolis_dest = "0x27657399177403a891CC7A22Bd6F2C00621Db7b0"

    test_usdc = 1 * 10**6
    full_usdc = 499999 * 10**6
    full_badger = Wei("9303.56 ether")
    full_wbtc = 3.68788871 * 10 ** 8

    console.print("Sending Amounts")

    snap.snap(name="Before Transfers")

    usdcToken.transfer(opolis_dest, test_usdc)

    snap.snap(name="After Transfers")
    snap.diff_last_two()

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx)
    data = safe.print_transaction(safe_tx)
    safe.post_transaction(safe_tx)
