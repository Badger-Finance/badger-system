from collections import OrderedDict

from config.rewards_config import rewards_config
from assistant.rewards.BadgerGeyserMock import BadgerGeyserMock
from assistant.subgraph.client import fetch_all_geyser_events
from brownie import *
from dotmap import DotMap
from helpers.constants import AddressZero
from rich.console import Console
from tqdm import trange

console = Console()

globalStartBlock = 11381000

def calc_geyser_stakes(key, geyser, periodStartBlock, periodEndBlock):
    globalStartTime = web3.eth.getBlock(globalStartBlock)["timestamp"]
    periodStartTime = web3.eth.getBlock(periodStartBlock)["timestamp"]
    periodEndTime = web3.eth.getBlock(periodEndBlock)["timestamp"]

    geyserMock = BadgerGeyserMock(key)
    geyserMock.set_current_period(periodStartTime, periodEndTime)

    # Collect actions from the total history
    console.print("\n[grey]Collect Actions: Entire History[/grey]")
    actions = collect_actions_from_events(geyser, globalStartBlock, periodEndBlock)

    # Process actions from the total history
    console.print("\n[grey]Process Actions: Entire History[/grey]")
    geyserMock = process_actions(geyserMock, actions, globalStartBlock, periodEndBlock)

    return calculate_token_distributions(
        geyser, geyserMock, periodStartTime, periodEndTime
    )


def calculate_token_distributions(
    geyser, geyserMock: BadgerGeyserMock, snapshotStartTime, periodEndTime
):
    """
    Tokens to Distribute:
    - get all distribution tokens
    - for each token, determine how many tokens will be distritbuted between the times specified
        - ((timeInClaimPeriod / totalTime) * initialLocked)
    """
    distributionTokens = geyser.getDistributionTokens()
    for token in distributionTokens:
        geyserMock.add_distribution_token(token)
        unlockSchedules = geyser.getUnlockSchedulesFor(token)
        for schedule in unlockSchedules:
            if rewards_config.debug:
                console.log(schedule)
            geyserMock.add_unlock_schedule(token, schedule)

    tokenDistributions = geyserMock.calc_token_distributions_in_range(
        snapshotStartTime, periodEndTime
    )
    userDistributions = geyserMock.calc_user_distributions(tokenDistributions)
    geyserMock.tokenDistributions = tokenDistributions
    geyserMock.userDistributions = userDistributions
    return userDistributions


def collect_actions(geyser):
    actions = DotMap()
    # == Process Unstaked ==
    data = fetch_all_geyser_events(geyser)
    staked = data["stakes"]
    unstaked = data["unstakes"]

    console.print(
        "Processing {} Staked events for Geyser {} ...".format(len(staked), geyser)
    )
    for event in staked:
        timestamp = event["timestamp"]
        user = event["user"]
        if user != AddressZero:
            if not actions[user][timestamp]:
                actions[user][timestamp] = []
            actions[user][timestamp].append(
                DotMap(
                    user=user,
                    action="Stake",
                    amount=int(event["amount"]),
                    userTotal=int(event["total"]),
                    stakedAt=int(event["timestamp"]),
                    timestamp=int(event["timestamp"]),
                )
            )
    # == Process Unstaked ==
    console.print(
        "Processing {} Unstaked events for Geyser {} ...".format(len(unstaked), geyser)
    )
    for event in unstaked:
        timestamp = event["timestamp"]
        user = event["user"]
        if user != AddressZero:
            if not actions[user][timestamp]:
                actions[user][timestamp] = []
            actions[user][timestamp].append(
                DotMap(
                    user=user,
                    action="Unstake",
                    amount=int(event["amount"]),
                    userTotal=int(event["total"]),
                    stakedAt=int(event["timestamp"]),
                    timestamp=int(event["timestamp"]),
                )
            )
    return actions


def collect_actions_from_events(geyser, startBlock, endBlock):
    """
    Construct a sequence of stake and unstake actions from events
    Unstakes for a given block are ALWAYS processed after the stakes, as we aren't tracking the transaction order within a block
    This could have extremely minor impact on rewards if stakes & unstakes happen during the same block (it would break if tracked the other way around, without knowing order)
    user -> timestamp -> action[]
    action: STAKE or UNSTAKE w/ parameters. (Stakes are always processed before unstakes within a given block)
    """
    contract = web3.eth.contract(geyser.address, abi=BadgerGeyser.abi)
    actions = DotMap()
    console.log("collecting actions")
    # Add stake actions
    for start in trange(startBlock, endBlock, 1000):
        console.log(startBlock)
        end = min(start + 999, endBlock)
        console.log("gettingLogs")
        logs = contract.events.Staked().getLogs(fromBlock=start, toBlock=end)
        console.log("gotLogs")
        console.log(logs)
        for log in logs:
            timestamp = log["args"]["timestamp"]
            user = log["args"]["user"]
            console.log("Staked", log["args"])
            if user != AddressZero:
                if not actions[user]:
                    actions[user] = OrderedDict()
                if not timestamp in actions[user]:
                    actions[user][timestamp] = []
                actions[user][timestamp].append(
                    DotMap(
                        user=user,
                        action="Stake",
                        amount=log["args"]["amount"],
                        userTotal=log["args"]["total"],
                        stakedAt=log["args"]["timestamp"],
                        timestamp=log["args"]["timestamp"],
                    )
                )

    # Add unstake actions
    for start in trange(startBlock, endBlock, 1000):
        end = min(start + 999, endBlock)
        logs = contract.events.Unstaked().getLogs(fromBlock=start, toBlock=end)
        for log in logs:
            timestamp = log["args"]["timestamp"]
            user = log["args"]["user"]
            console.log("Unstaked", log["args"])
            if user != AddressZero:
                if not actions[user]:
                    actions[user] = OrderedDict()
                if not timestamp in actions[user]:
                    actions[user][timestamp] = []
                actions[user][timestamp].append(
                    DotMap(
                        user=user,
                        action="Unstake",
                        amount=log["args"]["amount"],
                        userTotal=log["args"]["total"],
                        timestamp=log["args"]["timestamp"],
                    )
                )
    # Sort timestamps within each user
    for user, timestamps in actions.items():
        sortedDict = OrderedDict(sorted(timestamps.items()))
        actions[user] = sortedDict
    return actions


def process_actions(
    geyserMock: BadgerGeyserMock, actions, snapshotStartBlock, periodEndBlock
):
    """
    Add stakes
    Remove stakes according to unstaking rules (LIFO)
    """
    console.print("[green]== Processing Claim Period Actions ==[/green]\n")
    for user, userData in actions.items():
        table = []
        # console.print("\n= Processing actions for user: ", user + " =")
        latestTimestamp = 0

        # Iterate over actions, grouped by timestamp
        for timestamp, timestampEntries in userData.items():
            assert int(timestamp) > latestTimestamp
            for action in timestampEntries:
                if action.action == "Stake":
                    table.append(["stake", action["amount"], action["timestamp"]])
                    geyserMock.stake(action.user, action)
                if action.action == "Unstake":
                    table.append(["unstake", action["amount"], action["timestamp"]])
                    geyserMock.unstake(action.user, action)
            latestTimestamp = int(timestamp)

        # End accounting for user
        geyserMock.calc_end_share_seconds_for(user)

        # Print results
        # print(tabulate(table, headers=["action", "amount", "timestamp"]))
        # print("\n")
        user = geyserMock.users[user]
        table = []
        table.append([user.shareSecondsInRange, user.shareSeconds, user.total])
        # print(tabulate(table, headers=["shareSecondsInRange", "shareSeconds", "total"]))

    return geyserMock


# def ensure_archive_node():
#     fresh = web3.eth.call({"to": str(EMN), "data": EMN.totalSupply.encode_input()})
#     old = web3.eth.call(
#         {"to": str(EMN), "data": EMN.totalSupply.encode_input()}, SNAPSHOT_BLOCK
#     )
#     assert fresh != old, "this step requires an archive node"
