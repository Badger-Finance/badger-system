from helpers.constants import REWARDS_BLACKLIST, SETT_INFO
from scripts.systems.badger_system import BadgerSystem
from typing import Dict


@lru_cache(maxsize=128)
def chain_snapshot(badger: BadgerSystem, chain: str, block: int):
    """
    Take a snapshot of a chains sett balances at a certain block

    :param badger: badger system
    :param chain: chain to query
    :param block: block at which to query

    """
    chainBalances = fetch_chain_balances(chain, block)
    balancesBySett = {}

    for addr, balanceData in chainBalances.items():
        settAddress = balanceData["settAddress"]
        if settAddress not in balanceData:
            balanceData[settAddress] = {}
        balancesBySett[settAddress][addr] = balanceData["amount"]

    for sett, balances in list(balancesBySett.items()):
        balancesBySett[sett] = parse_sett_balances(sett, balances, chain)

    return balancesBySett

@lru_cache(maxsize=128)
def sett_snapshot(badger, chain, block,sett):
    return chain_snapshot(badger,chain,block)[sett]


@lru_cache(maxsize=128)
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

    settType = SETT_INFO[settAddress]["type"]
    settRatio = SETT_INFO[settAddress]["ratio"]
    userBalances = [
        UserBalance(addr, bal, settAddress) for addr, bal in balances.items()
    ]
    return UserBalances(userBalances, settType, settRatio)
