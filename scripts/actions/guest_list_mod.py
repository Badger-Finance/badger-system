from enum import Enum

import requests
from brownie import Wei, accounts, interface, rpc
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from helpers.registry import registry
from helpers.utils import val
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.uniswap_system import UniswapSystem
from helpers.gas_utils import gas_strategies

console = Console()

gas_strategies.set_default(gas_strategies.exponentialScalingFast)


def main():
    badger = connect_badger(load_deployer=True)
    dev = accounts.at("0xd41f7006bcb2B3d0F9C5873272Ebed67B37F80Dc", force=True)

    guestList = VipCappedGuestListBbtcUpgradeable.at(
        "0x7dD08c5a4Ce91Cf862223330dD373E36fe94189B"
    )

    guestRoot = guestList.guestRoot()
    userDepositCap = guestList.userDepositCap()
    totalDepositCap = guestList.totalDepositCap()
    owner = guestList.owner()

    newUserDepositCap = userDepositCap * 2
    newTotalDepositCap = int(totalDepositCap * 2.1)
    biggerCap = 525 * 10 ** 18

    console.print(
        {
            "guestRoot": guestRoot,
            "userDepositCap": userDepositCap,
            "totalDepositCap": totalDepositCap,
            "owner": owner,
            "newUserDepositCap": newUserDepositCap,
            "newTotalDepositCap": newTotalDepositCap,
            "biggerCap": biggerCap,
        }
    )

    guestList.setGuestRoot(EmptyBytes32, {"from": dev})
    guestList.setUserDepositCap(newUserDepositCap, {"from": dev})
    guestList.setTotalDepositCap(biggerCap, {"from": dev})

    guestRoot = guestList.guestRoot()
    userDepositCap = guestList.userDepositCap()
    totalDepositCap = guestList.totalDepositCap()
    owner = guestList.owner()

    console.print(
        {
            "guestRoot": guestRoot,
            "userDepositCap": userDepositCap,
            "totalDepositCap": totalDepositCap,
            "owner": owner,
            "newUserDepositCap": newUserDepositCap,
            "newTotalDepositCap": newTotalDepositCap,
            "biggerCap": biggerCap,
        }
    )
