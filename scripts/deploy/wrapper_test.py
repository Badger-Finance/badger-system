from pathlib import Path

import click
from eth_utils.address import is_canonical_address
import yaml
from brownie import (AffiliateTokenGatedUpgradeable, Wei, accounts, interface,
                     network, web3, rpc)
from eth_utils import is_checksum_address
from helpers.constants import MaxUint256
from semantic_version import Version
from helpers.token_utils import distribute_from_whales

def get_address(msg: str, default: str = None) -> str:
    val = click.prompt(msg, default=default)

    # Keep asking user for click.prompt until it passes
    while True:

        if is_checksum_address(val):
            return val
        elif addr := web3.ens.address(val):
            click.echo(f"Found ENS '{val}' [{addr}]")
            return addr

        click.echo(
            f"I'm sorry, but '{val}' is not a checksummed address or valid ENS record"
        )
        # NOTE: Only display default once
        val = click.prompt(msg)


def main():
    click.echo(f"You are using the '{network.show_active()}' network")
    if not rpc.is_active():
        dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    else:
        dev = accounts.at("0xDA25ee226E534d868f0Dd8a459536b03fEE9079b", force=True)
    click.echo(f"You are using: 'dev' [{dev.address}]")

    # BSC Test Vault
    token = interface.IERC20("0xEd2a8Ab49DcbCb8C27650cC8D5229Cefcad52e2a")
    vault = interface.VaultAPI("0x922F4E3926cc861765F116d77F4262d4429EEE3d")
    registry = interface.RegistryAPI("0xAfA32c074191E02f2b5F1baC8739629a66bD7893")

    # distribute_from_whales(dev, assets=["wbtc"])
    # gov = accounts.at(vault.governance(), force=True)
    
    # SpadaVault + Yearn Registry
    # token = interface.IERC20("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599")
    # vault = interface.VaultAPI("0x1Ae8Ccd120A05080d9A01C3B4F627F865685D091")
    # registry = interface.RegistryAPI("0x50c1a2ea0a861a967d9d0ffe2ae4012c2e053804")
    # strategy = "0xfFb5FdBBD42C567830f258A9C56aEfEA976e2310"
    
    depositLimit = Wei("100 gwei") # WBTC has 8 decimals
    depositAmount = Wei("0.1 gwei")

    # wrapper = AffiliateTokenGatedUpgradeable.deploy({"from": dev})
    
    # wrapper.initialize(
    #     token, registry, "Badger TEST yVault", "byvTEST", dev, {"from": dev}
    # )

    wrapper = AffiliateTokenGatedUpgradeable.at("0x50b20a12Acb15a413FE76FB82f9E524D3b0E8a69")

    # vault.setDepositLimit(depositLimit, {"from": gov})

    assert token.balanceOf(dev) >= depositAmount
    assert vault.token() == token
    assert registry.latestVault(token) == vault
    print(wrapper.bestVault())
    assert wrapper.bestVault() == vault

    print(wrapper.balanceOf(dev))

    token.approve(wrapper, MaxUint256, {"from": dev})
    wrapper.withdraw(depositAmount, {"from": dev, "gas_limit": 3000000, "allow_revert": True})
