from ape_safe import ApeSafe
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from helpers.coingecko import fetch_usd_price, fetch_usd_price_eth
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
from helpers.token_utils import BalanceSnapshotter
from helpers.utils import (
    fragments_to_shares,
    initial_fragments_to_current_fragments,
    shares_to_fragments,
    to_digg_shares,
    val,
)
from rich import pretty
from rich.console import Console
from scripts.systems.aragon_system import AragonSystem
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

console = Console()
pretty.install()

vote_ids = [10, 11, 12, 13, 14, 15, 16]


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

    diggToken = safe.contract(digg.token.address)
    bDigg = safe.contract_from_abi(badger.getSett("native.digg").address, "Sett", abi)
    rewardsEscrow = safe.contract_from_abi(
        badger.rewardsEscrow.address, "RewardsEscrow", RewardsEscrow.abi
    )
    teamVesting = safe.contract(badger.teamVesting.address)

    voting = safe.contract_from_abi(
        badger.daoBadgerTimelock.address, "IVoting", interface.IVoting.abi
    )
    aragon = AragonSystem()
    aragonVoting = aragon.getVotingAt(
        web3.toChecksumAddress("0xdc344bfb12522bf3fa58ef0d6b9a41256fc79a1b")
    )

    token_registry = registry.token_system()

    dev = accounts.at(badger.devMultisig.address, force=True)

    tokens = [
        token_registry.erc20_by_address(registry.tokens.farm),
        token_registry.erc20_by_address(registry.tokens.xSushi),
        token_registry.erc20_by_address(registry.curve.pools.sbtcCrv.token),
        token_registry.erc20_by_address(registry.curve.pools.renCrv.token),
        token_registry.erc20_by_address(registry.curve.pools.tbtcCrv.token),
        token_registry.erc20_by_address(registry.sushi.lpTokens.sushiWbtcWeth),
        token_registry.erc20_by_address(registry.tokens.dfd),
    ]

    snap = BalanceSnapshotter(tokens, [badger.devMultisig, badger.dao.agent])

    snap.snap(name="Before Transfers")

    for id in vote_ids:
        voting.vote(id, True, True)
        rewardsEscrow.call(
            aragonVoting, 0, aragonVoting.vote.encode_input(id, True, True)
        )
        teamVesting.call(
            aragonVoting, 0, aragonVoting.vote.encode_input(id, True, True)
        )

    snap.snap(name="After Transfers")
    snap.diff_last_two()

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx)
    data = safe.print_transaction(safe_tx)
    safe.post_transaction(safe_tx)
