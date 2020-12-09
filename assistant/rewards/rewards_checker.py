from tabulate import tabulate
from assistant.rewards.BadgerGeyserMock import BadgerGeyserMock
from scripts.systems.badger_system import BadgerSystem
from brownie import *
from rich.console import Console
from assistant.rewards.aws_utils import upload
import json
import brownie
from config.badger_config import badger_config, globalStartTime

console = Console()


def val(amount):
    return "{:,.6f}".format(amount / 1e18)


def sec(amount):
    return "{:,.1f}".format(amount / 1e12)


def get_distributed_in_range(key, geyser, startBlock, endBlock):
    periodEndTime = web3.eth.getBlock(endBlock)["timestamp"]
    periodStartTime = web3.eth.getBlock(startBlock)["timestamp"]

    geyserMock = BadgerGeyserMock(key)
    distributionTokens = geyser.getDistributionTokens()
    for token in distributionTokens:
        geyserMock.add_distribution_token(token)
        unlockSchedules = geyser.getUnlockSchedulesFor(token)
        for schedule in unlockSchedules:
            console.log(schedule)
            geyserMock.add_unlock_schedule(token, schedule)

    tokenDistributions = geyserMock.calc_token_distributions_in_range(
        periodStartTime, periodEndTime
    )

    return tokenDistributions


def getExpectedDistributionInRange(badger: BadgerSystem, startBlock, endBlock):
    distributions = {}
    for key, geyser in badger.geysers.items():
        dists = get_distributed_in_range(key, geyser, startBlock, endBlock)
        distributions[key] = dists

    console.log(distributions)
    # TODO: Only Badger for now
    total = 0
    for key, gains in distributions.items():
        total += gains["0x3472A5A71965499acd81997a54BBA8D852C6E53d"]

    return total
    # for key, dist in distributions.items():


def sum_claims(claims):
    total = 0
    for user, claim in claims.items():
        total += int(claim["cumulativeAmounts"][0])
    return total


def compare_rewards(
    badger: BadgerSystem,
    startBlock,
    endBlock,
    before_file,
    after_file,
    beforeContentHash,
):
    # Get these from files based on past root
    with open("rewards-1-" + "og" + ".json") as f:
        ec_file = json.load(f)

    before = before_file["claims"]
    after = after_file["claims"]
    ec = before_file["claims"]

    metadata = after_file["metadata"]

    currentMerkleData = badger.badgerTree.getCurrentMerkleData()
    expectedContentHash = str(currentMerkleData[1])

    assert beforeContentHash == expectedContentHash

    totalExpected = badger_config.geyserParams.unlockSchedules.badger[0].amount
    totalExpected += badger_config.geyserParams.unlockSchedules.uniBadgerWbtc[0].amount
    totalExpected += badger_config.geyserParams.unlockSchedules.bSbtcCrv[0].amount
    totalExpected += badger_config.geyserParams.unlockSchedules.bRenCrv[0].amount
    totalExpected += badger_config.geyserParams.unlockSchedules.bTbtcCrv[0].amount
    totalExpected += badger_config.geyserParams.unlockSchedules.bSuperRenCrvHarvest[
        0
    ].amount

    periodStartTime = web3.eth.getBlock(startBlock)["timestamp"]
    periodEndTime = web3.eth.getBlock(endBlock)["timestamp"]

    duration = periodEndTime - periodStartTime
    expectedInRange = totalExpected * duration // days(7)

    durationFromStart = periodEndTime - globalStartTime
    expectedFromStart = totalExpected * durationFromStart // days(7)

    print("totalExpected: ", totalExpected)
    print("duration: ", duration)
    print("expectedInRange: ", expectedInRange)

    ec_total = 314999999999999981912064

    # Expected gains must match up with the distributions from various rewards programs
    expectedGains = getExpectedDistributionInRange(badger, startBlock, endBlock)

    # Total claims must only increase
    sum_before = sum_claims(before)
    sum_after = sum_claims(after)
    sanitySum = Wei("600000 ether")

    table = []
    table.append(["block range", startBlock, endBlock])
    table.append(["duration", periodEndTime - periodStartTime, "-"])
    table.append(["sum before", sum_before, val(sum_before)])
    table.append(["sum after", sum_after, val(sum_after)])
    table.append(["expected gains", expectedGains, val(expectedGains)])
    table.append(
        ["expected after", sum_before + expectedGains, val(sum_before + expectedGains)]
    )
    table.append(
        [
            "diff",
            sum_after - (sum_before + expectedGains),
            val(sum_after - (sum_before + expectedGains)),
        ]
    )
    table.append(
        ["expectedFromStart", expectedFromStart, val(expectedFromStart),]
    )
    table.append(
        ["expectedInRange", expectedInRange, val(expectedInRange),]
    )
    table.append(
        ["Geyser Dist", sum_after - ec_total, val(sum_after - ec_total),]
    )
    table.append(
        ["From last period", sum_after - sum_before, val(sum_after - sum_before),]
    )
    table.append(
        ["Sanity Sum", sanitySum, "-",]
    )
    print(tabulate(table, headers=["key", "value", "scaled"]))

    assert sum_after >= sum_before
    assert sum_after <= sanitySum
    # assert sum_after - (sum_before + expectedGains) < 10000
    table = []
    # Each users' cumulative claims must only increase
    for user, claim in after.items():
        afterClaim = int(after[user]["cumulativeAmounts"][0])
        beforeClaim = 0
        ecClaim = 0
        if user in before:
            beforeClaim = int(before[user]["cumulativeAmounts"][0])
        if user in ec:
            ecClaim = int(ec[user]["cumulativeAmounts"][0])
        diff = afterClaim - beforeClaim

        # print([user, val(beforeClaim), val(afterClaim), val(diff)])
        epoch1 = beforeClaim - ecClaim
        epoch2 = afterClaim - beforeClaim

        assert afterClaim >= beforeClaim
        assert diff >= 0

        if epoch1 > 0:
            proportionGained = epoch2 / epoch1
        else:
            proportionGained = "+"

        if user in metadata:
            shareSeconds = metadata[user]["shareSeconds"]
            shareSecondsInRange = metadata[user]["shareSecondsInRange"]
            shareSecondsBefore = shareSeconds - shareSecondsInRange
            proportionInRange = shareSecondsInRange / shareSeconds
        else:
            shareSeconds = 0
            shareSecondsInRange = 0
            shareSecondsBefore = 0
            proportionInRange = 0

        table.append(
            [
                user,
                val(ecClaim),
                val(beforeClaim),
                val(afterClaim),
                val(diff),
                proportionGained,
                proportionInRange,
                # sec(shareSecondsInRange),
                # sec(shareSecondsBefore),
            ]
        )
        assert beforeClaim >= ecClaim
        assert afterClaim >= beforeClaim
    # print(
    #     tabulate(
    #         table,
    #         headers=[
    #             "user",
    #             "ec",
    #             "epoch 1 gains",
    #             "epoch 2 gains",
    #             "diff",
    #             "% gained" "% in range",
    #             # "shareSecondsInRange",
    #             # "shareSecondsBefore",
    #         ],
    #     )
    # )


def push_rewards(badger: BadgerSystem, afterContentHash):
    with open("rewards-1-" + afterContentHash + ".json") as f:
        after_file = json.load(f)

    keeper = badger.keeper

    claims = after_file["claims"]
    upload("rewards-1-" + afterContentHash + ".json")
    badger.badgerTree.proposeRoot(
        after_file["merkleRoot"],
        afterContentHash,
        after_file["cycle"],
        {"from": keeper},
    ),
    badger.badgerTree.approveRoot(
        after_file["merkleRoot"],
        afterContentHash,
        after_file["cycle"],
        {"from": keeper},
    ),


def test_claims(badger: BadgerSystem, startBlock, endBlock, before_file, after_file):
    before = before_file["claims"]
    claims = after_file["claims"]

    # Total claims must only increase
    total_claimable = sum_claims(claims)

    table = []
    # Each users' cumulative claims must only increase
    total_claimed = 0
    for user, claim in claims.items():
        claimed = badger.badgerTree.getClaimedFor(user, [badger.token.address])[1][0]
        print("Claim: ", user, claimed, claim["cumulativeAmounts"])
        if claimed == int(claim["cumulativeAmounts"][0]):
            print("SKIP!", user)
            continue
        accounts.at(user, force=True)
        pre = badger.token.balanceOf(user)
        tx = badger.badgerTree.claim(
            claim["tokens"],
            claim["cumulativeAmounts"],
            claim["index"],
            claim["cycle"],
            claim["proof"],
            {"from": user, "allow_revert": True},
        )
        print(tx.events)
        post = badger.token.balanceOf(user)
        diff = post - pre
        table.append([user, pre, post, diff, claim["cumulativeAmounts"][0]])
        total_claimed += int(claim["cumulativeAmounts"][0])
        assert post == pre + (int(claim["cumulativeAmounts"][0]) - claimed)
    print(tabulate(table, headers=["user", "before", "after", "diff", "claim"]))
    print(total_claimable, total_claimed, total_claimable - total_claimed)
