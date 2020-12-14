from brownie import *
from dotmap import DotMap
from tabulate import tabulate

from helpers.registry import whale_registry


def get_token_balances(accounts, tokens):
    balances = DotMap()
    for token in tokens:
        for account in accounts:
            balances.token.account = token.balanceOf(account)
    return balances

def distribute_from_whales(badger, recipient):

    print(len(whale_registry.items()))
    for key, whale in whale_registry.items():
        if key != "_pytestfixturefunction":
            print("transferring from whale", key, whale.toDict())
            forceEther = ForceEther.deploy({"from": recipient})
            recipient.transfer(forceEther, Wei("1 ether"))
            forceEther.forceSend(whale.whale, {"from": recipient})
            if whale.token:
                token = interface.IERC20(whale.token)
                token.transfer(
                    recipient, token.balanceOf(whale.whale) // 5, {"from": whale.whale}
                )


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
