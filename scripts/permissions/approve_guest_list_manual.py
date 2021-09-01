from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console
from ape_safe import ApeSafe

strategies_to_approve = [
    "native.hbtcCrv",
    "native.pbtcCrv",
    "native.obtcCrv",
    "native.bbtcCrv",
    "native.tricrypto",
    "native.tricryptoDos",
]
guest_lists_by_id = ["native.cvxCrv", "native.cvx"]


def main():
    """
    Add contracts manually to guest list. They will now be approved regardless of merkle root situation
    """
    badger = connect_badger()
    safe = ApeSafe(badger.testMultisig.address)
    helper = ApeSafeHelper(badger, safe)

    for strategy_key in strategies_to_approve:
        strategy_address = badger.getStrategy(strategy_key).address
        source = helper.contract_from_abi(
            badger.getStrategy(strategy_key).address,
            "StrategyConvexStakingOptimizer",
            StrategyConvexStakingOptimizer.abi,
        )

        for guest_list_key in guest_lists_by_id:
            guestList = helper.contract_from_abi(
                badger.getGuestList(guest_list_key).address,
                "VipCappedGuestListBbtcUpgradeable",
                VipCappedGuestListBbtcUpgradeable.abi,
            )
            console.print(
                f"Approve [green]{strategy_address}[/green] on Guest list [yellow]{guest_list_key} ({guestList.address})[/yellow]"
            )
            guestList.setGuests([strategy_address], [True])
            assert guestList.guests(strategy_address) == True

    helper.publish()
