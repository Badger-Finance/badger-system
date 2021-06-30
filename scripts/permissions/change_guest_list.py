from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console
from ape_safe import ApeSafe

setts = ["native.cvxCrv", "native.cvx"]

def main():
    """
    Add contracts manually to guest list. They will now be approved regardless of merkle root situation
    """
    badger = connect_badger()
    safe = ApeSafe(badger.testMultisig.address)
    helper = ApeSafeHelper(badger, safe)

    for sett_key in setts:
        sett = helper.contract_from_abi(badger.getSett(sett_key).address, "SettV4", SettV4.abi)
        guestList = badger.getGuestList(sett_key)

        old_state = {
            'guestList': sett.guestList(),
            'guestRoot': guestList.guestRoot(),
            'totalCap': guestList.totalDepositCap(),
            'userCap': guestList.userDepositCap(),
            'wrapper': guestList.wrapper(),
        }

        sett.setGuestList(guestList)

        print("proxyAdmin", badger.getProxyAdmin(guestList))

        new_state = {
            'guestList': sett.guestList(),
            'guestRoot': guestList.guestRoot(),
            'totalCap': guestList.totalDepositCap(),
            'userCap': guestList.userDepositCap(),
            'wrapper': guestList.wrapper(),
        }

        assert new_state['guestList'] != old_state['guestList']
        assert new_state['guestList'] == guestList

        assert new_state['guestRoot'] == old_state['guestRoot']
        assert new_state['totalCap'] == old_state['totalCap']
        assert new_state['userCap'] == old_state['userCap']
        assert new_state['wrapper'] == old_state['wrapper']


    helper.publish()
