from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256, EmptyBytes32
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console
from ape_safe import ApeSafe

guest_lists_by_id = ["native.cvxCrv", "native.cvx"]
root = EmptyBytes32


def main():
    """
    Add contracts manually to guest list. They will now be approved regardless of merkle root situation
    """
    badger = connect_badger()
    safe = ApeSafe(badger.testMultisig.address)
    helper = ApeSafeHelper(badger, safe)

    for guest_list_key in guest_lists_by_id:
        guestList = helper.contract_from_abi(
            badger.getGuestList(guest_list_key).address,
            "VipCappedGuestListBbtcUpgradeable",
            VipCappedGuestListBbtcUpgradeable.abi,
        )
        console.print(
            f"Set guest root to [green]{root}[/green] on Guest list [yellow]{guest_list_key} ({guestList.address})[/yellow]"
        )
        guestList.setGuestRoot(root)
        assert guestList.guestRoot() == root

    helper.publish()
