from brownie import (
    accounts,
    UpgradeableChildERC20,
    UpgradableProxy,
    UpgradeableMetaToken,
)

from helpers.registry import registry
from helpers.constants import AddressZero
from helpers.proxy_utils import deploy_proxy_admin, deploy_proxy


def test_meta_token():
    gov = accounts[3]

    tokenName = "Interest Bearing Bitcoin"
    tokenSymbol = "ibBTC"
    decimals = 8

    proxyAdmin = deploy_proxy_admin(gov)
    metaTokenLogic = UpgradeableMetaToken.deploy({"from": gov})
    metaToken = deploy_proxy(
        "MetaTokenIbBTC",
        UpgradeableMetaToken.abi,
        proxyAdmin.address,
        metaTokenLogic.initialize.encode_input(
            tokenName,
            tokenSymbol,
            decimals,
        ),
    )

    childLogic = UpgradeableChildERC20.deploy({"from": gov})
    childProxy = UpgradableProxy.deploy(AddressZero, {"from": gov})
    childProxy.updateAndCall(childLogic, childLogic.initialize.encode_input(
        f"{tokenName} - matic bridge",
        f"{tokenSymbol}-matic",
        decimals,
        registry.matic.childChainManager,
        metaToken,
    ))
