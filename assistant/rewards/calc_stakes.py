from assistant.rewards.BadgerGeyserMock import BadgerGeyserMock
from brownie import *
from dotmap import DotMap
from helpers.constants import AddressZero
from rich.console import Console
from tqdm import trange

console = Console()


def calc_geyser_stakes(geyser, globalStartBlock, snapshotStartBlock, periodEndBlock):
    console.print(
        " Geyser initial snapshot for " + geyser.address,
        {"from": snapshotStartBlock, "to": periodEndBlock},
    )

    globalStartTime = web3.eth.getBlock(globalStartBlock)["timestamp"]
    snapshotStartTime = web3.eth.getBlock(snapshotStartBlock)["timestamp"]
    periodEndTime = web3.eth.getBlock(periodEndBlock)["timestamp"]

    geyserMock = BadgerGeyserMock()
    geyserMock.set_current_period(snapshotStartTime, periodEndTime)

    console.log(
        "blocks between",
        {
            "globalStartBlock": globalStartBlock,
            "snapshotStartBlock": snapshotStartBlock,
            "periodEndBlock": periodEndBlock,
            "globalStartTime": globalStartTime,
            "snapshotStartTime": snapshotStartTime,
            "periodEndTime": periodEndTime,
        },
    )

    # Collect actions from the past, and generate the initial state of stakes
    console.print("\n[grey]Collect Actions: Historical[/grey]")
    pre_actions = collect_actions(geyser, globalStartBlock, snapshotStartBlock - 1)
    console.print("\n[grey]Process Actions: Historical[/grey]")
    geyserMock = process_snapshot(
        geyserMock, pre_actions, globalStartBlock, snapshotStartBlock - 1
    )

    # Collect actions from the claim period
    console.print("\n[grey]Collect Actions: Claim Period[/grey]")
    actions = collect_actions(geyser, snapshotStartBlock, periodEndBlock)

    # Process shareSeconds from the claims period
    console.print("\n[grey]Process Actions: Claim Period[/grey]")
    geyserMock = process_actions(
        geyserMock, actions, snapshotStartBlock, periodEndBlock
    )
    console.log(geyserMock.getUserWeights())

    return calculate_token_distributions(
        geyser, geyserMock, snapshotStartTime, periodEndTime
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
            console.log(schedule)
            geyserMock.add_unlock_schedule(token, schedule)

    tokenDistributions = geyserMock.calc_token_distributions_in_range(
        snapshotStartTime, periodEndTime
    )
    userDistributions = geyserMock.calc_user_distributions(tokenDistributions)
    return userDistributions


def collect_actions(geyser, startBlock, endBlock):
    """
    Construct a sequence of stake and unstake actions from events
    Unstakes for a given block are ALWAYS processed after the stakes, as we aren't tracking the transaction order within a block
    This could have extremely minor impact on rewards if stakes & unstakes happen during the same block (it would break if tracked the other way around, without knowing order)
    user -> timestamp -> action[]
    action: STAKE or UNSTAKE w/ parameters. (Stakes are always processed before unstakes within a given block)
    """
    contract = web3.eth.contract(geyser.address, abi=BadgerGeyser.abi)
    actions = DotMap()

    # Add stake actions
    for start in trange(startBlock, endBlock, 1000):
        end = min(start + 999, endBlock)
        logs = contract.events.Staked().getLogs(fromBlock=start, toBlock=end)
        for log in logs:
            timestamp = log["args"]["timestamp"]
            user = log["args"]["user"]
            console.log("Staked", log["args"])
            if user != AddressZero:
                if not actions[user][timestamp]:
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
                if not actions[user][timestamp]:
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
    console.log("actions from events", actions.toDict())
    return actions


def process_snapshot(geyserMock, actions, startBlock, endBlock):
    """
    Generate current set of Stakes from historical data
    """
    startTime = web3.eth.getBlock(startBlock)["timestamp"]
    endTime = web3.eth.getBlock(endBlock)["timestamp"]

    console.print("[green]== Processing to Snapshot ==[/green]\n")
    console.log(
        "Processing actions for Snapshot",
        {"startTime": startTime, "endTime": endTime},
        actions.toDict(),
    )
    for user, data in actions.items():
        console.log(" processing user", user)
        for timestamp in data.values():
            for action in timestamp:
                if action.action == "Stake":
                    geyserMock.stake(action.user, action, trackShareSeconds=False)
                if action.action == "Unstake":
                    geyserMock.unstake(action.user, action, trackShareSeconds=False)

    console.print("= User stakes at pre-snapshot =", style="dim cyan")
    geyserMock.printState()
    return geyserMock


def process_actions(
    geyserMock: BadgerGeyserMock, actions, snapshotStartBlock, periodEndBlock
):
    """
    Add stakes
    Remove stakes according to unstaking rules (LIFO)
    """
    startTime = web3.eth.getBlock(snapshotStartBlock)["timestamp"]
    endTime = web3.eth.getBlock(periodEndBlock)["timestamp"]

    console.print("[green]== Processing Claim Period Actions ==[/green]\n")
    console.log(
        "Processing actions for Claim Period",
        {"startTime": startTime, "endTime": endTime},
        actions.toDict(),
    )
    for user, userData in actions.items():
        console.log(" processing User", user)
        for timestamp, timestampEntries in userData.items():
            console.log(" timestamp collection", timestamp, timestampEntries)
            for action in timestampEntries:
                if action.action == "Stake":
                    geyserMock.stake(action.user, action)
                if action.action == "Unstake":
                    geyserMock.unstake(action.user, action)

    geyserMock.calc_end_share_seconds()
    console.print("= User stakes after actions =", style="dim cyan")
    geyserMock.printState()
    return geyserMock


# def ensure_archive_node():
#     fresh = web3.eth.call({"to": str(EMN), "data": EMN.totalSupply.encode_input()})
#     old = web3.eth.call(
#         {"to": str(EMN), "data": EMN.totalSupply.encode_input()}, SNAPSHOT_BLOCK
#     )
#     assert fresh != old, "this step requires an archive node"
