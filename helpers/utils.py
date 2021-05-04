import time
from brownie import *
from dotenv import load_dotenv
from rich.console import Console
from tabulate import tabulate
import requests
from discord import Webhook, RequestsWebhookAdapter, Embed
import os
console = Console()
load_dotenv()

# Assert approximate integer
def approx(actual, expected, percentage_threshold):
    print(actual, expected, percentage_threshold)
    diff = int(abs(actual - expected))
    # 0 diff should automtically be a match
    if diff == 0:
        return True
    return diff < (actual * percentage_threshold // 100)

def tx_wait():
    if rpc.is_active():
        chain.mine()
    else:
        time.sleep(15)

def Eth(value):
    return value / 1e18

def to_tabulate(title, data):
    """
    Print dictionary data in table format
    """
    table = []
    for key, value in data.items():
        table.append([key, value])
    console.print("\n[bold cyan]{}[/bold cyan]".format(title))
    print(tabulate(table, headers=["key", "value"]))
    print("\n")

def shares_to_fragments(shares):
    digg_contract = interface.IDigg("0x798D1bE841a82a273720CE31c822C61a67a601C3")
    current_fragments = digg_contract.sharesToFragments(shares)

    return current_fragments

def fragments_to_shares(fragments_scaled):
    digg_contract = interface.IDigg("0x798D1bE841a82a273720CE31c822C61a67a601C3")
    fragments = int(fragments_scaled * 10 ** 9)
    shares = fragments * digg_contract._sharesPerFragment()
    return shares

def to_digg_shares(initial_fragments_scaled):
    if initial_fragments_scaled == 0:
        return 0
    digg_contract = interface.IDigg("0x798D1bE841a82a273720CE31c822C61a67a601C3")
    initial_fragments = int(initial_fragments_scaled * 10 ** 9)
    shares = initial_fragments * digg_contract._initialSharesPerFragment()
    current_fragments = digg_contract.sharesToFragments(shares)

    console.print("Digg Conversion", {
        'input':initial_fragments_scaled,
        'scaledInput':initial_fragments,
        'shares':shares,
        'fragments':current_fragments,
        'fragmentsScaled': val(current_fragments, decimals=9),
        'ratio': current_fragments / initial_fragments
    })
    return shares

def initial_fragments_to_current_fragments(initial_fragments_scaled):
    digg_contract = interface.IDigg("0x798D1bE841a82a273720CE31c822C61a67a601C3")

    initial_fragments = int(initial_fragments_scaled * 10 ** 9)

    shares = initial_fragments * digg_contract._initialSharesPerFragment()

    current_fragments = digg_contract.sharesToFragments(shares)

    # console.print("Digg Conversion", {
    #     'input':initial_fragments_scaled,
    #     'scaledInput':initial_fragments,
    #     'shares':shares,
    #     'fragments':current_fragments,
    #     'fragmentsScaled': val(current_fragments, decimals=9),
    #     'ratio': current_fragments / initial_fragments
    # })
    return current_fragments

def digg_shares_to_initial_fragments(digg, shares):
    """
    Convert shares to initial fragments scale
    For negative numbers (for example as part of a diff), use abs first
    """
    scaled = 0
    if shares < 0:
        shares = abs(shares)
        scaled = digg.sharesToScaledShares(shares)
        scaled = -scaled
    else:
        scaled = digg.sharesToScaledShares(shares)
    return val(scaled)


def digg_shares(value):
    return value / 1e68


def val(amount=0, decimals=18, token=None):
    # return amount
    # return "{:,.0f}".format(amount)
    # If no token specified, use decimals
    if token:
        decimals = interface.IERC20(token).decimals()

    return "{:,.18f}".format(amount / 10 ** decimals)


def sec(amount):
    return "{:,.1f}".format(amount / 1e12)


def snapBalancesMatchForToken(snap, otherSnap, tokenKey):
    for entityKey in snap.entityKeys:
        balance = snap.balances(tokenKey, entityKey)
        otherBalance = otherSnap.balances(tokenKey, entityKey)
        if balance != otherBalance:
            return False
    return True


def snapSharesMatchForToken(snap, otherSnap, tokenKey):
    for entityKey in snap.entityKeys:
        shares = snap.shares(tokenKey, entityKey)
        otherShares = otherSnap.shares(tokenKey, entityKey)
        if shares != otherShares:
            return False
    return True

def send_transaction_to_discord(
    tx, 
    strategy_name,
    amount=None, 
    success=True
    ):
    webhook = Webhook.from_url(os.getenv("DISCORD_WEBHOOK_URL"), adapter=RequestsWebhookAdapter())
    etherscan_url = f"https://etherscan.io/tx/{tx.txid}"
    if success:
        embed = Embed(
            title="**Keeper transaction SUCCESS**"
        )
    else:
        embed = Embed(
            title="**Keeper transaction FAILED**"
        )
    if "harvest" in tx.fn_name:
        embed.add_field(
            name="Keeper Action", value=f"Harvest ${str(round(amount))} for {strategy_name}.", inline=False
        )
        embed.add_field(
            name="Etherscan Transaction", value=f"{etherscan_url}", inline=False
        )
        webhook.send(embed=embed, username="Sushi Harvester")
    elif "tend" in tx.fn_name:
        embed.add_field(
            name="Keeper Action", value=f"Tend ${str(round(amount))} for {strategy_name}.", inline=False
        )
        embed.add_field(
            name="Etherscan Transaction", value=f"{etherscan_url}", inline=False
        )
        webhook.send(embed=embed, username="Sushi Tender")