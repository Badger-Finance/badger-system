from brownie import *
import brownie
from rich.console import Console

"""
Test for upgrading DIGG to allow for remDIGG minting
"""

console = Console()

ADDRESSES = [
    "0xfed1CAe770ca1cD19D7bcC7Fa61d3325A9d5D164",
    "0x03387d5015f88Aea995e790F18eF7FF9dfa0943C",
    "0x4F9a04Bf67a65A59Ef0beB8dcC83f7f3cC5C5D23",
    "0x482c741b0711624d1f462E56EE5D8f776d5970dC",
    "0xD6d2Fcc947e62B21CedbeD336893A2Ba47cd8dac",
    "0x1Da722CfA8B0dFda57CF8D787689039C7A63F049",
    "0x6d0BBe84eBa47434a0004fc65797B87eF1C913b7",
    "0x186E20ae3530520C9F3E6C46F2f5d1062b784761",
    "0x4dc804eaa4c9cC4839f0D9c8824CCE7A0C7Dc10a",
]


def test_upgrade_and_mint(digg_proxy, proxy_admin, governance_timelock):
    # record current digg information
    prev_total_supply = digg_proxy.totalSupply()
    prev_name = digg_proxy.name()
    prev_decimals = digg_proxy.decimals()
    prev_total_shares = digg_proxy.totalShares()
    prev_shares_per_fragment = digg_proxy._sharesPerFragment()
    prev_owner = digg_proxy.owner()
    prev_monetary_policy = digg_proxy.monetaryPolicy()
    prev_symbol = digg_proxy.symbol()
    prev_initial_shares_per_fragment = digg_proxy._initialSharesPerFragment()
    prev_balances = {}
    for address in ADDRESSES:
        prev_balances[address] = digg_proxy.balanceOf(address)

    # deploy new digg logic
    owner = accounts.at(prev_owner, force=True)
    new_digg_logic = UFragments.deploy({"from": owner})

    # upgrade digg proxy
    proxy_admin.upgrade(digg_proxy, new_digg_logic, {"from": governance_timelock})

    # check storage + random sampled balances
    assert prev_total_supply == digg_proxy.totalSupply()
    assert prev_name == digg_proxy.name()
    assert prev_decimals == digg_proxy.decimals()
    assert prev_total_shares == digg_proxy.totalShares()
    assert prev_shares_per_fragment == digg_proxy._sharesPerFragment()
    assert prev_owner == digg_proxy.owner()
    assert prev_monetary_policy == digg_proxy.monetaryPolicy()
    assert prev_symbol == digg_proxy.symbol()
    assert prev_initial_shares_per_fragment == digg_proxy._initialSharesPerFragment()
    for address in ADDRESSES:
        assert prev_balances[address] == digg_proxy.balanceOf(address)
    prev_dev_msig_balance = digg_proxy.balanceOf(prev_owner)

    # mint digg
    digg_proxy.oneTimeMint({"from": owner})

    # double check address balances to make sure that minting did not effect them
    for address in ADDRESSES:
        assert prev_balances[address] == digg_proxy.balanceOf(address)

    # make sure minting cannot be done again
    with brownie.reverts("Mint already complete"):
        digg_proxy.oneTimeMint({"from": owner})

    # test transfer functionality
    sender = accounts.at(ADDRESSES[0], force=True)
    receiver = accounts.at(ADDRESSES[1], force=True)
    prev_sender_balance = digg_proxy.balanceOf(sender)
    prev_receiver_balance = digg_proxy.balanceOf(receiver)
    send_amount = 1000000000
    digg_proxy.transfer(receiver, send_amount, {"from": sender})
    assert digg_proxy.balanceOf(sender) == prev_sender_balance - send_amount
    assert digg_proxy.balanceOf(receiver) == prev_receiver_balance + send_amount

    # check total supply = total supply + mint amount
    assert digg_proxy.totalSupply() == prev_total_supply + 52942035500

    # check balanceOf dev msig = balanceOf dev msig + mint amount
    new_dev_msig_balance = digg_proxy.balanceOf(prev_owner)
    assert prev_dev_msig_balance + 52942035500 == new_dev_msig_balance

    # test sweep
    link = interface.IERC20("0x514910771AF9Ca656af840dff83E8264EcF986CA")
    prev_balance = link.balanceOf(digg_proxy)
    dev_prev_balance = link.balanceOf(owner)
    assert prev_balance > 0
    digg_proxy.sweep("0x514910771AF9Ca656af840dff83E8264EcF986CA", {"from": owner})
    assert link.balanceOf(digg_proxy) == 0
    assert link.balanceOf(owner) == dev_prev_balance + prev_balance

    # test no balance sweep
    shiba = interface.IERC20("0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce")
    assert shiba.balanceOf(digg_proxy) == 0
    with brownie.reverts("No balance to sweep"):
        digg_proxy.sweep("0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce", {"from": owner})
