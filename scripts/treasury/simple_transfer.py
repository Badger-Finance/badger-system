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

console = Console()


def main():
    """
    Transfer badger to recipient, ensuring they are approved as recipient first
    Use test tx, full tx model
    Can convert from dollar value
    """

    badger = connect_badger()
    multisig = badger.devMultisig

    safe = ApeSafe(multisig.address)
    helper = ApeSafeHelper(badger, safe)

    rewardsEscrow = safe.contract(badger.rewardsEscrow.address)

    recipient = badger.badgerRewardsManager

    # token = badger.token
    # amount = Wei("30000 ether")

    token = badger.digg.token
    amount = Wei("2 gwei")

    if not rewardsEscrow.isApproved(recipient):
        rewardsEscrow.approveRecipient(recipient)

    rewardsEscrow.transfer(token, recipient, amount)

    helper.publish()
