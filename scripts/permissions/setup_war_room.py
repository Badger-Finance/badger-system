from brownie import *
from scripts.connect_account import connect_account
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from ape_safe import ApeSafe


def main():
    dev = connect_account()
    warRoom = WarRoomGatedProxy.at("0xCD3271021e9b35EF862Dd98AFa826b8b5198826d")
    warRoom.initialize(
        "0xDA25ee226E534d868f0Dd8a459536b03fEE9079b",
        ["0x29F7F8896Fb913CF7f9949C623F896a154727919"],
        {"from": dev},
    )

    # print_access_control(warRoom)

    # multi = badger.devMultisig
    # safe = ApeSafe(multi.address)
    # helper = ApeSafeHelper(badger, safe)

    # Set all guardians to war room

    """
    Many contracts are pausable. We need to include all contracts in a registry to do a proper debugging view of this. 
    Revising the contract design to take a single access control list will standardize this process.

    contract-level list overrides are available on ACL.
    contract-level specific overrides for certain roles are available.

    """
    # for sett_id in badger.getAllSettIds():
    #     if sett_id in ["yearn.wbtc"]:
    #         continue

    #     sett = helper.contract_from_abi(
    #         badger.getSett(sett_id).address, "SettV3", SettV3.abi
    #     )
    #     strategy = helper.contract_from_abi(
    #         badger.getStrategy(sett_id).address,
    #         "StrategyCvxCrvHelper",
    #         StrategyCvxCrvHelper.abi,
    #     )

    # helper.publish()
