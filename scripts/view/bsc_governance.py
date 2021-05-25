from brownie import *
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from config.badger_config import badger_config
from helpers.console_utils import console


def verify_proxy_admin(proxyAdmin, contract):
    assert proxyAdmin.getProxyAdmin(contract) == proxyAdmin
    console.print("proxyAdmin verified ✅", contract.address, proxyAdmin)
    proxyAdmin.getProxyImplementation(contract)


def verify_governance(contract, expected):
    assert contract.governance() == expected
    console.print("governance verified ✅", contract.address, expected)


def main():
    badger = connect_badger()

    admin = badger.devProxyAdmin

    controller = badger.getController("native")

    assert admin.owner() == badger.devMultisig

    verify_proxy_admin(admin, controller)
    verify_governance(controller, badger.opsMultisig)

    for settId in badger.getAllSettIds():
        if settId == "native.test":
            continue
        sett = badger.getSett(settId)
        strategy = badger.getStrategy(settId)

        verify_proxy_admin(admin, sett)
        verify_proxy_admin(admin, strategy)

        verify_governance(sett, badger.opsMultisig)
        verify_governance(strategy, badger.opsMultisig)
