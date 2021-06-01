from helpers.token_utils import BalanceSnapshotter
from ape_safe import ApeSafe
from helpers.coingecko import fetch_usd_price, fetch_usd_price_eth

from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from helpers.constants import *
from helpers.gnosis_safe import (
    ApeSafeHelper,
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

tokens = registry.token_system()


def crv_swap(badger, safe: ApeSafe, amount_in, max_slippage):
    wbtc = safe.contract(tokens.erc20_by_key("wbtc").address)
    renbtc = safe.contract(tokens.erc20_by_key("renbtc").address)

    indicies = {"wbtc": 1, "renbtc": 0}

    # sbtc = interface.ICurveFi("0x7fc77b5c7614e1533320ea6ddc2eb61fa00a9714")

    sbtc = safe.contract_from_abi(
        address=web3.toChecksumAddress("0x7fc77b5c7614e1533320ea6ddc2eb61fa00a9714"),
        name="ICurveFi",
        abi=interface.ICurveFi.abi,
    )

    # wbtc.approve(sbtc, amount_in)
    renbtc.approve(sbtc, amount_in)

    required_out = amount_in - int(amount_in * max_slippage)
    print(required_out)

    sbtc.exchange(indicies["renbtc"], indicies["wbtc"], amount_in, required_out)


def main():
    badger = connect_badger()
    digg = badger.digg
    safe = ApeSafe(badger.devMultisig.address)

    abi = Sett.abi

    badgerToken = safe.contract(badger.token.address)
    diggToken = safe.contract(digg.token.address)
    bBadger = safe.contract_from_abi(
        badger.getSett("native.badger").address, "Sett", abi
    )
    bDigg = safe.contract_from_abi(badger.getSett("native.digg").address, "Sett", abi)
    rewardsEscrow = safe.contract(badger.rewardsEscrow.address)

    # Exchange renBTC for wBTC

    wbtc = tokens.erc20_by_key("wbtc")
    renbtc = tokens.erc20_by_key("renbtc")

    snap = BalanceSnapshotter([wbtc, renbtc], [badger.devMultisig])

    snap.snap(name="Before", print=True)

    crv_swap(badger, safe, amount_in=367606868, max_slippage=0.005)

    snap.snap(name="After")
    snap.diff_last_two()

    helper = ApeSafeHelper(badger, safe)
    helper.publish()
