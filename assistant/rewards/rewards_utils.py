from brownie import *
from rich.console import Console
from collections import Counter
from assistant.subgraph.client import (
    fetch_sett_balances,
    fetch_geyser_events,
)
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.classes.UserBalance import UserBalance, UserBalances
from functools import lru_cache

blacklist = [
    "0x19D97D8fA813EE2f51aD4B4e04EA08bAf4DFfC28",
    "0x6dEf55d2e18486B9dDfaA075bc4e4EE0B28c1545",
    "0xd04c48A53c111300aD41190D63681ed3dAd998eC",
    "0xb9D076fDe463dbc9f915E5392F807315Bf940334",
    "0x235c9e24D3FB2FAFd58a2E49D454Fdcd2DBf7FF1",
    "0xAf5A1DECfa95BAF63E0084a35c62592B774A2A87",
    "0x1862A18181346EBd9EdAf800804f89190DeF24a5",
    "0x758a43ee2bff8230eeb784879cdcff4828f2544d",
    "0xC17078FDd324CC473F8175Dc5290fae5f2E84714",
    "0x88128580ACdD9c04Ce47AFcE196875747bF2A9f6",
    "0x7e7E112A68d8D2E221E11047a72fFC1065c38e1a",
]

cream_addresses = {"native.badger": "0x8b950f43fcac4931d408f1fcda55c6cb6cbf3096"}
console = Console()


def get_cumulative_claimable_for_token(claim, token):
    tokens = claim["tokens"]
    amounts = claim["cumulativeAmounts"]

    console.log(tokens, amounts)

    for i in range(len(tokens)):
        address = tokens[i]
        if token == address:
            return int(amounts[i])

    # If address was not found
    return 0


def get_claimed_for_token(data, token):
    tokens = data[0]
    amounts = data[1]

    for i in range(len(tokens)):
        address = tokens[i]
        if token == address:
            return amounts[i]


def publish_new_root(badger, root, contentHash):
    """
    Publish new root from local file
    """

    tree = badger.badgerTree

    rootProposer = accounts.at(tree.getRoleMember(ROOT_PROPOSER_ROLE, 0), force=True)
    rootValidator = accounts.at(tree.getRoleMember(ROOT_VALIDATOR_ROLE, 0), force=True)

    lastProposeEndBlock = tree.lastProposeEndBlock()
    currentCycle = tree.currentCycle()

    endBlock = chain.height

    tree.proposeRoot(
        root,
        contentHash,
        currentCycle + 1,
        lastProposeEndBlock + 1,
        endBlock,
        {"from": rootProposer},
    )

    chain.mine()

    tree.approveRoot(
        root,
        contentHash,
        currentCycle + 1,
        lastProposeEndBlock + 1,
        endBlock,
        {"from": rootValidator},
    )


def keccak(value):
    return web3.toHex(web3.keccak(text=value))


def combine_rewards(rewardsList, cycle, badgerTree):
    combinedRewards = RewardsList(cycle, badgerTree)
    for rewards in rewardsList:
        for user, claims in rewards.claims.items():
            for token, claim in claims.items():
                combinedRewards.increase_user_rewards(user, token, claim)
    return combinedRewards


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


def get_latest_event_block(firstEvent, events):
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


def calc_meta_farm_rewards(badger, name, startBlock, endBlock):
    console.log("Calculating rewards between {} and {}".format(startBlock, endBlock))
    startBlock = int(startBlock)
    endBlock = int(endBlock)
    startBlockTime = web3.eth.getBlock(startBlock)["timestamp"]
    endBlockTime = web3.eth.getBlock(endBlock)["timestamp"]
    sett = badger.getSett(name)

    balances = calculate_sett_balances(badger, name, endBlock)
    # TODO: Do we want to use  multiple snapshots
    # here or just the end?
    return balances


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
    allBalances = UserBalances()
    for userBalances in balances:
        allBalances = allBalances + userBalances
    return allBalances


@lru_cache(maxsize=None)
def calculate_sett_balances(badger, name, currentBlock):
    console.log("Fetching {} sett balances".format(name))
    sett = badger.getSett(name)
    underlyingToken = sett.address
    settType = ["", ""]
    if "uni" in name or "sushi" in name:
        settType[0] = "halfLP"
    if "crv" in name or name == "experimental.sushiIBbtcWbtc":
        settType[0] = "fullLP"
    if "badger" in name.lower() or "digg" in name.lower() or "eth" in name.lower():
        settType[1] = "nonNative"
    else:
        settType[1] = "native"

    settBalances = fetch_sett_balances(name, underlyingToken.lower(), currentBlock)
    geyserBalances = {}
    creamBalances = {}
    # Digg doesn't have a geyser so we have to ignore it
    noGeysers = ["native.digg", "experimental.sushiIBbtcWbtc", "experimental.digg"]
    if name not in noGeysers:
        geyserAddr = badger.getGeyser(name).address.lower()
        geyserEvents = fetch_geyser_events(geyserAddr, currentBlock)
        geyserBalances = calc_balances_from_geyser_events(geyserEvents)
        settBalances[geyserAddr] = 0

    balances = {}
    for b in [settBalances, geyserBalances, creamBalances]:
        balances = dict(Counter(balances) + Counter(b))
    # Get rid of blacklisted and negative balances
    for addr, balance in balances.items():
        if addr in blacklist or balance < 0:
            del balances[addr]

    userBalances = [
        UserBalance(addr, bal, underlyingToken, settType)
        for addr, bal in balances.items()
    ]
    console.log("\n")
    return UserBalances(userBalances)
