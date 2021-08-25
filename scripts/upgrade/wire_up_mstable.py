from brownie import *
from helpers.constants import *
from helpers.constants import MaxUint256
from ape_safe import ApeSafe
from helpers.gnosis_safe import ApeSafeHelper
from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console

contracts_to_approve = ["0x4459A591c61CABd905EAb8486Bf628432b15C8b1"]

contracts = {
    "VoterProxy": "0x10D96b1Fd46Ce7cE092aA905274B8eD9d4585A6E",
    "imBTC-vault": "0x599D92B453C010b1050d31C364f6ee17E819f193",
    "imBTC-strategy": "0xd409C506742b7f76f164909025Ab29A47e06d30A",
    "fPmBtcHBtc-vault": "0x26B8efa69603537AC8ab55768b6740b67664D518",
    "fPmBtcHBtc-strategy": "0x54D06A0E1cE55a7a60Ee175AbCeaC7e363f603f3",
}


def main():
    badger = connect_badger()
    safe = ApeSafe(badger.devMultisig.address)
    helper = ApeSafeHelper(badger, safe)

    controller = helper.contract_from_abi(
        badger.getController("experimental").address, "Controller", Controller.abi
    )

    asset = "0x17d8cbb6bce8cee970a4027d1198f6700a7a6c24"
    sett = helper.contract_from_abi(contracts["imBTC-vault"], "SettV3", SettV3.abi)
    strat = helper.contract_from_abi(
        contracts["imBTC-strategy"],
        "StrategyConvexStakingOptimizer",
        StrategyConvexStakingOptimizer.abi,
    )

    print(sett.token(), strat.want())

    assert sett.token() == asset
    assert strat.want() == asset

    controller.setVault(asset, sett)
    controller.approveStrategy(asset, strat)
    controller.setStrategy(asset, strat)

    asset = "0x48c59199Da51B7E30Ea200a74Ea07974e62C4bA7"
    sett = helper.contract_from_abi(contracts["fPmBtcHBtc-vault"], "SettV3", SettV3.abi)
    strat = helper.contract_from_abi(
        contracts["fPmBtcHBtc-strategy"],
        "StrategyConvexStakingOptimizer",
        StrategyConvexStakingOptimizer.abi,
    )

    assert sett.token() == asset
    assert strat.want() == asset

    controller.setVault(asset, sett)
    controller.approveStrategy(asset, strat)
    controller.setStrategy(asset, strat)

    helper.publish()
