import json
import requests
from brownie import *
from rich.console import Console
from collections import Counter
from assistant.subgraph.client import (
    fetch_sett_balances,
    fetch_sett_transfers,
    fetch_geyser_events,
    fetch_cream_balances
)
from assistant.rewards.classes.User import User
from assistant.rewards.classes.RewardsList import RewardsList

cream_addresses = {
    "native.badger":"0x8b950f43fcac4931d408f1fcda55c6cb6cbf3096"
}

console = Console()
badger_api_url = "https://laiv44udi0.execute-api.us-west-1.amazonaws.com/staging/v2"

def keccak(value):
    return web3.toHex(web3.keccak(text=value))

def combine_rewards(rewardsList,cycle, badgerTree):
    totals = RewardsList(cycle,badgerTree)
    for rewards in rewardsList:
        for user,claims in rewards.claims.items():
            for token,claim in claims.items():
                totals.increase_user_rewards(user,token,claim)
    return totals

def process_cumulative_rewards(current, new: RewardsList):
    result = RewardsList(new.cycle, new.badgerTree)

    # Add new rewards
    for user, claims in new.claims.items():
        for token, claim in claims.items():
            result.increase_user_rewards(user, token, claim)

    # Add existing rewards
    for user, userData in current["claims"].items():
        for i in range(len(userData["tokens"])):
            token = userData["tokens"][i]
            amount = userData["cumulativeAmounts"][i]
            result.increase_user_rewards(user, token, int(amount))

    # result.printState()
    return result

def sum_rewards(sources, cycle, badgerTree):
    """
    Sum rewards from all given set of rewards' list, returning a single rewards list
    """
    totals = RewardsList(cycle, badgerTree)
    total = 0
    # For each rewards list entry
    for key, rewardsSet in sources.items():
        # Get the claims data
        claims = rewardsSet["claims"]
        metadata = rewardsSet["metadata"]

        # Add values from each user
        for user, userData in claims.items():
            totals.track_user_metadata(user, metadata)

            # For each token
            for token, tokenAmount in userData.items():
                totals.increase_user_rewards(user, token, tokenAmount)

                total += tokenAmount
    totals.badgerSum = total
    # totals.printState()
    return totals

def get_latest_event_block(firstEvent,events):
    try:
        event_index = events.index(firstEvent)
    except ValueError:
        return -1
    if event_index - 1 >= 0 and event_index - 1 < len(events):
        # startBlock starts with the last harvest that happened 
        latestEvent = events[event_index - 1] 
        return latestEvent["blockNumber"]
    else:
        return -1

def calc_meta_farm_rewards(badger,name, startBlock, endBlock):
    console.log("Calculating rewards between {} and {}".format(startBlock,endBlock))
    startBlock = int(startBlock)
    endBlock = int(endBlock)
    startBlockTime = web3.eth.getBlock(startBlock)["timestamp"]
    endBlockTime = web3.eth.getBlock(endBlock)["timestamp"]
    console.log(startBlockTime)
    console.log(endBlockTime)
    settId = badger.getSett(name).address.lower()
    geyserId = badger.getGeyser(name).address.lower()

    settBalances = fetch_sett_balances(settId, startBlock)
    if len(settBalances) == 0:
            return []
    if len(settBalances) != 0:
        console.log("Found {} balances".format(len(settBalances)))
        console.log("Geyser amount in sett Balance: {}".format(settBalances[geyserId]/1e18))
        settBalances[geyserId] = 0

    geyserEvents = fetch_geyser_events(geyserId, startBlock)
    geyserBalances = calc_balances_from_geyser_events(geyserEvents)
    user_state = combine_balances([settBalances,geyserBalances])
    # TODO: Do we want to use snapshot here or do we use shareSeconds 
    return user_state


def calc_balances_from_geyser_events(geyserEvents):
    balances = {}
    events = [*geyserEvents["stakes"], *geyserEvents["unstakes"]]
    events = sorted(events, key=lambda e: e["timestamp"])
    currentTime = 0
    for event in events:
        timestamp = int(event["timestamp"])
        assert timestamp >= currentTime
        balances[event["user"]] = int(event["total"])


    console.log("Sum of geyser balances: {}".format(sum(balances.values()) / 10 ** 18))
    console.log("Fetched {} geyser balances".format(len(balances)))
    return balances

def combine_balances(balances):
    allBalances = {}
    for b in balances:
        allBalances = dict(Counter(allBalances) + Counter(b))
    return allBalances

def calculate_sett_balances(badger, name, sett, currentBlock):
    settBalances = fetch_sett_balances(sett.address.lower(), currentBlock)
    geyserBalances = {}
    creamBalances = {}
    # Digg doesn't have a geyser so we have to ignore it
    if name != "native.digg":
        geyserAddr = badger.getGeyser(name).address.lower()
        geyserEvents = fetch_geyser_events(
            geyserAddr, currentBlock
        )
        geyserBalances = calc_balances_from_geyser_events(geyserEvents)
        settBalances[geyserAddr] = 0
    if name in ["native.badger"]:
        settUnderlyingToken = interface.ERC20(sett.token())
        creamBalances = fetch_cream_balances("crB{}".format(settUnderlyingToken.symbol()))
    if name in cream_addresses:
        settBalances[cream_addresses[name]] = 0

    return combine_balances([settBalances, geyserBalances, creamBalances])