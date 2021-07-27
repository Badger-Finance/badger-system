from helpers.constants import REWARDS_BLACKLIST, SETT_INFO
from scripts.systems.badger_system import BadgerSystem
from assistant.rewards.classes.UserBalance import UserBalances, UserBalance
from assistant.subgraph.client import fetch_chain_balances
from functools import lru_cache
from rich.console import Console
from typing import Dict
from brownie import web3

console = Console()


@lru_cache(maxsize=128)
def chain_snapshot(badger: BadgerSystem, chain: str, block: int):
    """
    Take a snapshot of a chains sett balances at a certain block

    :param badger: badger system
    :param chain: chain to query
    :param block: block at which to query

    """
    chainBalances = fetch_chain_balances(chain, block - 50)
    balanceInfo = {}
    balancesBySett = {}

    for addr, balanceData in chainBalances.items():
        settAddress = balanceData["settAddress"]
        if settAddress not in balanceInfo:
            balanceInfo[settAddress] = {}
        balanceInfo[settAddress][addr] = balanceData["amount"]
    for settAddr, balances in list(balanceInfo.items()):
        console.log(settAddr)
        console.log(balances)
        settBalances = parse_sett_balances(settAddr, balances, chain)
        console.log("Fetched {} balances for sett {}".format(len(balances), settAddr))
        balancesBySett[settAddr] = settBalances

    return balancesBySett


@lru_cache(maxsize=128)
def sett_snapshot(badger, chain, block, sett):
    return chain_snapshot(badger, chain, block)[sett]


def parse_sett_balances(settAddress: str, balances: Dict[str, int], chain: str):
    """
    Blacklist balances and add metadata for boost
    :param balances: balances of users:
    :param chain: chain where balances come from
    """
    for addr, balance in list(balances.items()):
        if addr.lower() in REWARDS_BLACKLIST:
            console.log(
                "Removing {} from balances".format(REWARDS_BLACKLIST[addr.lower()])
            )
            del balances[addr]

    settType, settRatio = get_sett_info(settAddress)
    userBalances = [
        UserBalance(addr, bal, settAddress) for addr, bal in balances.items()
    ]
    return UserBalances(userBalances, settType, settRatio)


def get_sett_info(settAddress):
    info = SETT_INFO.get(
        web3.toChecksumAddress(settAddress), {"type": "nonNative", "ratio": 1}
    )
    return info["type"], info["ratio"]
