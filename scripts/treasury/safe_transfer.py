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

    rewardsEscrow = helper.contract_from_abi(
        badger.rewardsEscrow.address, "RewardsEscrow", RewardsEscrow.abi
    )
    vesting = helper.contract_from_abi(
        badger.digg.daoDiggTimelock.address, "SimpleTimelock", SimpleTimelock.abi
    )
    dfd = helper.contract_from_abi(web3.toChecksumAddress("0x20c36f062a31865bed8a5b1e512d9a1a20aa333a"), "IERC20", interface.IERC20.abi)
    diggToken = helper.contract_from_abi(
        badger.digg.token.address, "IERC20", interface.IERC20.abi
    )

    transfers = [
        # TransferOp(badger.paymentsMultisig, badger.token, Wei("51222 ether")),
        TransferOp(badger.badgerTree, badger.token, Wei("40000 ether")),
        TransferOp(badger.badgerTree, diggToken, Wei("1 gwei")),
        TransferOp(badger.badgerTree, dfd, Wei("96000 ether")),
        # TransferOp(badger.badgerRewardsManager, badger.token, Wei("10000 ether")),
        # TransferOp(badger.badgerRewardsManager, diggToken, Wei("2 gwei")),
    ]

    snap = BalanceSnapshotter(
        [badger.token, badger.digg.token, dfd],
        [
            badger.badgerTree,
            badger.badgerRewardsManager,
            badger.devMultisig,
            badger.rewardsEscrow,
            badger.paymentsMultisig,
        ],
    )
    snap.snap()

    rewards_escrow_tokens = [badger.token]

    for transfer in transfers:
        recipient = transfer.recipient
        token = transfer.token
        amount = transfer.amount

        console.print("Transfer", recipient, token, amount)

        # Transfer from rewards escrow
        if token.address in rewards_escrow_tokens:
            if not rewardsEscrow.isApproved(recipient):
                rewardsEscrow.approveRecipient(recipient)
            rewardsEscrow.transfer(token, recipient, amount)

        # Default: Transfer from treasury
        else:
            # Unlock from vesting
            # if token.address == badger.digg.token.address:
            #     vesting.release(amount)
            token.transfer(recipient, amount)

    snap.snap()
    snap.diff_last_two()

    helper.publish()
