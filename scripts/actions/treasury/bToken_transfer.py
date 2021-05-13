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

    recipient = accounts.at("0x8Ea8a668f89a9A203d37D8a1E27e38De5bEb8380", force=True)

    safe = ApeSafe(badger.devMultisig.address)

    abi = Sett.abi

    badgerToken = safe.contract(badger.token.address)
    diggToken = safe.contract(digg.token.address)
    bBadger = safe.contract_from_abi(
        badger.getSett("native.badger").address, "Sett", abi
    )
    bDigg = safe.contract_from_abi(badger.getSett("native.digg").address, "Sett", abi)

    snap = BalanceSnapshotter(
        [badgerToken, diggToken, bBadger, bDigg],
        [badger.devMultisig, badger.deployer, badger.rewardsEscrow, recipient],
    )

    snap.snap(name="Before Transfers", print=True)

    bBadger_amount = Wei("4585.501571219566358195 ether")
    bDigg_amount = Wei("6.96203478522210066 ether")

    # Transfer receieved amounts to badger deployer for transfer over bridge
    bBadger.transfer(recipient, bBadger_amount)
    bDigg.transfer(recipient, bDigg_amount)

    snap.snap(name="After Transfers")
    snap.diff_last_two()

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx)
    data = safe.print_transaction(safe_tx)
    safe.post_transaction(safe_tx)
