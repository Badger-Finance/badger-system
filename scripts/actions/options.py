from helpers.token_utils import (
    BalanceSnapshotter,
    distribute_from_whales,
    distribute_test_ether,
    get_token_balances,
)
from ape_safe import ApeSafe
from brownie import *
from gnosis.safe.safe import Safe
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.registry import registry
from helpers.utils import shares_to_fragments, to_digg_shares, val

from helpers.gnosis_safe import (
    ApeSafeHelper,
    GnosisSafe,
    MultisigTx,
    MultisigTxMetadata,
    convert_to_test_mode,
    exec_direct,
)
from helpers.proxy_utils import deploy_proxy
from helpers.time_utils import days, hours

console = Console()

amount = 177739297999371831309
amount = 177739000000000000000


def main():
    badger = connect_badger()

    bDigg = badger.getSett("native.digg")

    # rug = accounts.at(web3.toChecksumAddress("0x533e3c0e6b48010873b947bddc4721b1bdff9648"), force=True)
    # print(bDigg.balanceOf(rug))
    # bDigg.transfer(badger.devMultisig, amount, {"from": rug})

    bDigg_to_deposit = amount
    print("bDigg_to_deposit", bDigg_to_deposit)
    round_1 = Wei("1 ether")
    round_2 = bDigg_to_deposit - round_1

    safe = ApeSafe(badger.devMultisig.address)
    bDigg = safe.contract_from_abi(
        "0x7e7E112A68d8D2E221E11047a72fFC1065c38e1a", "Sett", Sett.abi
    )
    dropt = safe.contract_from_abi(
        web3.toChecksumAddress("0x02660b54750efab874fb43b4b613c135c7815eef"),
        "SyntheticToken",
        SyntheticToken.abi,
    )
    kpiOptions = safe.contract_from_abi(
        web3.toChecksumAddress("0xbc044745f137d4693c2aa823c760f855254fad42"),
        "ExpiringMultiParty",
        ExpiringMultiParty.abi,
    )

    snap = BalanceSnapshotter([bDigg, dropt], [badger.devMultisig, kpiOptions, dropt])

    snap.snap()

    bDigg.approve(kpiOptions, bDigg_to_deposit)
    kpiOptions.create([round_1], [int(round_1 * 1000)])
    kpiOptions.create([round_2], [int(round_2 * 1000)])
    chain.mine()

    snap.snap()

    snap.diff_last_two()

    helper = ApeSafeHelper(badger, safe)
    helper.publish()
