from helpers.token_utils import BalanceSnapshotter
from ape_safe import ApeSafe
from helpers.coingecko import fetch_usd_price, fetch_usd_price_eth

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


def main():
    badger = connect_badger("deploy-final.json")
    digg = badger.digg
    admin = badger.devProxyAdmin
    multisig = badger.devMultisig
    contracts = badger.contracts_upgradeable
    deployer = badger.deployer

    expectedMultisig = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    assert multisig == expectedMultisig

    safe = ApeSafe(badger.devMultisig.address)

    abi = Sett.abi

    badgerToken = safe.contract(badger.token.address)
    diggToken = safe.contract(digg.token.address)
    bBadger = safe.contract_from_abi(
        badger.getSett("native.badger").address, "Sett", abi
    )
    bDigg = safe.contract_from_abi(badger.getSett("native.digg").address, "Sett", abi)
    rewardsEscrow = safe.contract(badger.rewardsEscrow.address)

    total_usd = 255000

    badger_usd = fetch_usd_price(badger.token.address)
    digg_usd = fetch_usd_price(digg.token.address)
    eth_usd = fetch_usd_price_eth()

    badger_to_send = Wei(str(total_usd / badger_usd) + " ether")
    digg_to_send = Wei(str(total_usd / digg_usd) + " gwei")

    table = []
    table.append(["badger", badger_to_send, badger_usd])
    table.append(["digg", digg_to_send, digg_usd])
    table.append(["eth", 0, eth_usd])
    print(tabulate(table, headers=["asset", "to send", "$ price"]))

    snap = BalanceSnapshotter(
        [badgerToken, diggToken, bBadger, bDigg],
        [badger.devMultisig, badger.deployer, badger.rewardsEscrow]
    )

    snap.snap(name="Before Transfers")

    # Transfer assets to multisig
    rewardsEscrow.transfer(badgerToken, badger.devMultisig, badger_to_send)
    rewardsEscrow.transfer(diggToken, badger.devMultisig, digg_to_send)

    snap.snap(name="After Transfers")
    snap.diff_last_two()

    # Deposit bBadger
    badgerToken.approve(bBadger.address, badger_to_send)
    tx = bBadger.deposit(badger_to_send)
    print(tx.events)

    # Deposit bDigg
    diggToken.approve(bDigg.address, digg_to_send)
    tx = bDigg.deposit(digg_to_send)
    print(tx.events)

    snap.snap(name="After Deposits")
    snap.diff_last_two()

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx)
    data = safe.print_transaction(safe_tx)
    safe.post_transaction(safe_tx)


