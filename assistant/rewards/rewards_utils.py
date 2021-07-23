from helpers.constants import NO_GEYSERS, CONVEX_SETTS
from brownie import *
from rich.console import Console
from collections import Counter
from assistant.subgraph.client import (
    fetch_sett_balances,
    fetch_geyser_events,
)
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.classes.UserBalance import UserBalance, UserBalances
from helpers.constants import NO_GEYSERS, REWARDS_BLACKLIST
from functools import lru_cache


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
    if "crv" in name.lower() or name == "experimental.sushiIBbtcWbtc":
        settType[0] = "fullLP"
    if "badger" in name.lower() or "digg" in name.lower() or "eth" in name.lower():
        settType[1] = "nonNative"
    else:
        settType[1] = "native"

    settBalances = fetch_sett_balances(name, underlyingToken.lower(), currentBlock)
    geyserBalances = {}
    creamBalances = {}

    if name not in NO_GEYSERS:

        geyserAddr = badger.getGeyser(name).address.lower()
        geyserEvents = fetch_geyser_events(geyserAddr, currentBlock)
        geyserBalances = calc_balances_from_geyser_events(geyserEvents)
        settBalances[geyserAddr] = 0

    balances = {}
    for b in [settBalances, geyserBalances, creamBalances]:
        balances = dict(Counter(balances) + Counter(b))

    # Get rid of blacklisted and negative balances
    for addr, balance in list(balances.items()):
        if addr in blacklist or balance < 0:
            del balances[addr]

    # Testing for peak address
    # balances["0x41671BA1abcbA387b9b2B752c205e22e916BE6e3".lower()] = 10000
    userBalances = [
        UserBalance(addr, bal, underlyingToken, settType)
        for addr, bal in balances.items()
    ]
    console.log("\n")
    return UserBalances(userBalances)
