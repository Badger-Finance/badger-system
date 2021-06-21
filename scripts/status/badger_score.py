import requests
from brownie import *
from rich.console import Console
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from assistant.rewards.rewards_utils import calculate_sett_balances
from assistant.subgraph.client import fetch_wallet_balances,fetch_nfts
from helpers.constants import NON_NATIVE_SETTS

badger = connect_badger()

console = Console()
scores = {}

def unix_time_to_block(time):
    url = "https://api.etherscan.io/api?module=block&action=getblocknobytime&timestamp={}&closest=before".format(
        time
    )
    data = requests.get(url).json()
    return int(data["result"])

def sett_users_above_zero(sett, block):
    users = []

    balances = calculate_sett_balances(badger, sett, block)

    for user in balances:
        if user.balance > 0:
            users.append(user.address)

    return users


def badger_staking_and_lp(block):

    bbadger = sett_users_above_zero("native.badger", block)
    badgerUniLp = sett_users_above_zero("native.uniBadgerWbtc", block)
    badgerSlp = sett_users_above_zero("native.sushiBadgerWbtc")
    return list(set([*bbadger, *badgerUniLp, *badgerSlp])), 1


def digg_staking_and_lp(block):

    bdigg = sett_users_above_zero("native.digg", block)
    diggUniLp = sett_users_above_zero("native.uniDiggWbtc", block)
    diggSushiLp = sett_users_above_zero("native.sushiDiggWbtc", block)
    return list(set([*bdigg, *diggUniLp, *diggSushiLp])), 3


def governance_participant(unix_time):
    url = "https://hub.snapshot.page/api/voters?from=0to={}&spaces=badgerdao.eth".format(
        unix_time
    )
    voters = requests.get(url).json()
    voters = [v["address"].lower() for v in voters]
    return voters, 1


def non_native_sett_user(block):
    users = []
    for sett in NON_NATIVE_SETTS:
        u = sett_users_above_zero(sett, block)
        users = [*users, u]

    return list(set(users)), 1


def ibbtc_sett_user(block):
    users = []
    _, _1, ibbtc_balances = fetch_wallet_balances(badger.digg, block)
    for addr, bal in ibbtc_balances.items():
        if bal > 0:
            users.append(addr)

    return users, 2

def add_score(addresses,score,cond):
    for addr in addresses:
        addr = addr.lower()
        if addr not in scores:
            scores[addr] = {}
            
        scores[addr][cond] = score

def main():
    unix_time = 1623884400
    block = unix_time_to_block(unix_time_to_block)
    console.log(block)
    
    condition_4 = fetch_nfts(block)
    console.log(condition_4)
    
    condition_1, score = badger_staking_and_lp(block)
    add_score(condition_1,score,"cond1")
    
    condition_2,score_2 = digg_staking_and_lp(block)
    add_score(condition_2,score_2,"cond2")
    
    condition_3,score_3 = governance_participant(unix_time)
    add_score(condition_3,score_3,"cond3")
    
    add_score(condition_4,1,"cond4")
    
    condition_5,score_5 = non_native_sett_user(block)
    add_score(condition_5,score_5,"cond5")
    
    condition_6,score_6 = ibbtc_sett_user(block)
    add_score(condition_6,score_6,"cond6")
    
    

    
    
