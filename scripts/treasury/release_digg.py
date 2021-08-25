from enum import Enum
from ape_safe import ApeSafe

import requests
from brownie import Wei, accounts, interface, rpc
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper, GnosisSafe, MultisigTxMetadata
from helpers.registry import registry
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.uniswap_system import UniswapSystem
from helpers.token_utils import BalanceSnapshotter

console = Console()


class TransferOp:
    def __init__(self, recipient, token, amount):
        self.recipient = recipient
        self.token = token
        self.amount = amount


def main():
    """
    Transfer badger to recipient, ensuring they are approved as recipient first
    Use test tx, full tx model
    Can convert from dollar value

    Assumes each token is a safeContract
    """

    badger = connect_badger()
    digg = badger.digg
    multisig = badger.devMultisig

    safe = ApeSafe(multisig.address)
    helper = ApeSafeHelper(badger, safe)

    vesting = helper.contract_from_abi(
        badger.digg.daoDiggTimelock.address, "SimpleTimelock", SimpleTimelock.abi
    )

    snap = BalanceSnapshotter(
        [badger.token, badger.digg.token],
        [badger.devMultisig, vesting],
    )
    snap.snap()

    bal = digg.token.balanceOf(vesting)

    vesting.release(bal)

    snap.snap()
    snap.diff_last_two()

    helper.publish()
