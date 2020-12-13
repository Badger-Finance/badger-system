from helpers.time_utils import days, hours
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


def diff_rewards(
    badger: BadgerSystem, before_file, after_file,
):
    a = before_file["claims"]
    b = after_file["claims"]

    table = []
    # Each users' cumulative claims must only increase
    for user, claim in b.items():
        afterClaim = int(b[user]["cumulativeAmounts"][0])
        beforeClaim = 0
        if user in a:
            beforeClaim = int(a[user]["cumulativeAmounts"][0])
        diff = afterClaim - beforeClaim

        proportionGained = afterClaim / beforeClaim
        assert proportionGained > 0.98
        assert proportionGained < 1.25

        table.append(
            [user, val(beforeClaim), val(afterClaim), val(diff), proportionGained,]
        )
    print(tabulate(table, headers=["user", "a", "b", "diff", "% gained"],))


def compare_rewards(
    badger: BadgerSystem,
    startBlock,
    endBlock,
    before_file,
    after_file,
    beforeContentHash,
):
    before = before_file["claims"]
    after = after_file["claims"]

    print(startBlock, endBlock, beforeContentHash)

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

    # Expected gains must match up with the distributions from various rewards programs
    expectedGains = getExpectedDistributionInRange(badger, startBlock, endBlock)

    # Total claims must only increase
    sum_before = sum_claims(before)
    sum_after = sum_claims(after)
    sanitySum = Wei("1100000 ether")

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
    table.append(["Geyser Dist", sum_after, val(sum_after)])
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

        if user in before:
            beforeClaim = int(before[user]["cumulativeAmounts"][0])
        diff = afterClaim - beforeClaim

        assert afterClaim >= beforeClaim
        assert diff >= 0

        if beforeClaim == 0:
            proportionGained = 1
        elif diff > 0:
            proportionGained = afterClaim / beforeClaim
        else:
            proportionGained = "+"

        if user in metadata:
            shareSeconds = metadata[user]["shareSeconds"]
            # shareSecondsInRange = metadata[user]["shareSecondsInRange"]
            # shareSecondsBefore = shareSeconds - shareSecondsInRange
            # proportionInRange = shareSecondsInRange / shareSeconds
        else:
            shareSeconds = 0
            # shareSecondsInRange = 0
            # shareSecondsBefore = 0
            # proportionInRange = 0

        table.append(
            [user, val(beforeClaim), val(afterClaim), val(diff), proportionGained,]
        )
        assert afterClaim >= beforeClaim
    # print(
    #     tabulate(
    #         table,
    #         headers=[
    #             "user",
    #             "before gains",
    #             "after gains",
    #             "diff",
    #             "% gained"
    #         ],
    #     )
    # )


def push_rewards(badger: BadgerSystem, afterContentHash):
    with open("rewards-1-" + afterContentHash + ".json") as f:
        after_file = json.load(f)

    upload("rewards-1-" + afterContentHash + ".json")
    badger.badgerTree.proposeRoot(
        after_file["merkleRoot"],
        afterContentHash,
        after_file["cycle"],
        {"from": badger.keeper},
    ),

    badger.badgerTree.approveRoot(
        after_file["merkleRoot"],
        afterContentHash,
        after_file["cycle"],
        {"from": badger.guardian},
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
