from brownie import *
from dotmap import DotMap
from tabulate import tabulate

from helpers.registry import WhaleRegistryAction, whale_registry
from rich.console import Console
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.uniswap_system import UniswapSystem

console = Console()


def get_token_balances(accounts, tokens):
    balances = DotMap()
    for token in tokens:
        for account in accounts:
            balances.token.account = token.balanceOf(account)
    return balances


def distribute_from_whales(recipient):

    console.print(
        "[green] 🐋 Transferring assets from whales for {} assets... 🐋 [/green]".format(
            len(whale_registry.items())
        )
    )

    # Normal Transfers
    for key, whale_config in whale_registry.items():
        # Handle special cases after all standard distributions
        if whale_config.special:
            continue
        if key != "_pytestfixturefunction":
            console.print(" -> {}".format(key))
            distribute_from_whale(whale_config, recipient)

    # Special Transfers
    for key, whale_config in whale_registry.items():
        if not whale_config.special:
            continue
        if whale_config.action == WhaleRegistryAction.POPULATE_NEW_SUSHI_LP:
            # Populate LP pair and distribute
            # NOTE: Account should have been distributed both underlying components previously
            sushiswap = SushiswapSystem()
            sushiswap.addMaxLiquidity(
                whale_config.actionParams["token0"], whale_config.actionParams["token1"], recipient
            )


def distribute_from_whale(whale_config, recipient, percentage=0.2):
    if whale_config.action == WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT:
        forceEther = ForceEther.deploy({"from": recipient})
        recipient.transfer(forceEther, Wei("1 ether"))
        forceEther.forceSend(whale_config.whale, {"from": recipient})

    token = interface.IERC20(whale_config.token)
    token.transfer(
        recipient,
        token.balanceOf(whale_config.whale) * percentage,
        {"from": whale_config.whale},
    )


def distribute_test_ether(recipient, amount):
    """
    On test environments, transfer ETH from default ganache account to specified account
    """
    assert accounts[0].balance() >= amount
    accounts[0].transfer(recipient, amount)


def getTokenMetadata(address):
    token = interface.IERC20(address)
    name = token.name()
    symbol = token.symbol()
    return (name, symbol, address)


def distribute_meme_nfts(badger, user):
    honeypot_params = DotMap(
        token=badger.token,
        amount=Wei("2500 ether"),
        nftIndicies=[97, 98, 99, 100, 101, 102],
        meme="0xe4605d46Fd0B3f8329d936a8b258D69276cBa264",
        badgerCollection="0x14dC10FA6E4878280F9CA0D9f32dDAEa8C7d4d45",
    )

    memeLtd = interface.IMemeLtd(honeypot_params.meme)
    badgerCollection = accounts.at(honeypot_params.badgerCollection, force=True)

    for index in honeypot_params.nftIndicies:
        console.print("Minting MEME NFT {} for {}...".format(index, user))
        memeLtd.mint(user, index, 1, "0x", {"from": badgerCollection})

    for index in honeypot_params.nftIndicies:
        assert memeLtd.balanceOf(user, index) > 0


def balances(contracts, tokens):
    # Headers
    headers = []
    headers.append("contract")

    for token in tokens:
        headers.append(token.symbol())

    # Balances
    data = []
    for name, c in contracts.items():
        cData = []
        cData.append(name)
        for token in tokens:
            cData.append(token.balanceOf(c) / 1e18)
        data.append(cData)
    print(tabulate(data, headers=headers))
