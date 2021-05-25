from brownie import (
    accounts,
    UpgradeableChildERC20,
    UpgradableProxy,
)

from helpers.registry import registry
from helpers.constants import AddressZero


def test_meta_token():
    gov = accounts[3]
    childLogic = UpgradeableChildERC20.deploy({"from": gov})
    childProxy = UpgradableProxy.deploy(AddressZero, {"from": gov})
    childProxy.updateAndCall(childLogic, childLogic.initialize.encode_input(
        "Interest Bearing Bitcoin",
        "ibBTC",
        8,
        registry.matic.childChainManager,
        # TODO: Impl meta token contract and validate test that
        # proxied deposits/withdraws work from child chain manager.
        AddressZero,
    ))
