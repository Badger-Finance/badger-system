from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console
from ape_safe import ApeSafe

to_approve = [
    "native.hbtcCrv",
    "native.pbtcCrv",
    "native.obtcCrv",
    "native.bbtcCrv",
    "native.tricrypto",
    "native.tricryptoDos",
]
destination_setts = ["native.cvxCrv", "native.cvx"]


def main():
    badger = connect_badger()
    safe = ApeSafe(badger.testMultisig.address)
    helper = ApeSafeHelper(badger, safe)

    for source_key in to_approve:
        source = badger.getStrategy(source_key).address
        # source = helper.contract_from_abi(badger.getStrategy(source_key), "StrategyConvexStakingOptimizer", StrategyConvexStakingOptimizer.abi)
        for dest_key in destination_setts:
            destination = helper.contract_from_abi(
                badger.getSett(dest_key).address, "SettV3", SettV3.abi
            )
            console.print(
                f"Approve [green]{source}[/green] on Sett [yellow]{dest_key} ({destination.address})"
            )
            destination.approveContractAccess(source)

    helper.publish()
