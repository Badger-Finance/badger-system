import time
from brownie.network.gas.strategies import GasNowStrategy
from scripts.systems.digg_system import connect_digg
from helpers.time_utils import days, hours
from tabulate import tabulate
from scripts.systems.badger_system import BadgerSystem
from brownie import *
from rich.console import Console
from assistant.rewards.aws_utils import upload
import json
from helpers.utils import val
from helpers.constants import TOKENS_TO_CHECK, DIGG, BADGER

console = Console()


gas_strategy = GasNowStrategy("rapid")


def get_digg_contract():
    digg_contract = interface.IDigg(DIGG)
    return digg_contract


def sec(amount):
    return "{:,.1f}".format(amount / 1e12)


def get_distributed_in_range(key, geyser, startBlock, endBlock):
    periodEndTime = web3.eth.getBlock(endBlock)["timestamp"]
    periodStartTime = web3.eth.getBlock(startBlock)["timestamp"]

    geyserMock = BadgerGeyserMock(key)
    distributionTokenss = geyser.getDistributionTokenss()
    for token in distributionTokenss:
        geyserMock.add_distribution_token(token)
        unlockSchedules = geyser.getUnlockSchedulesFor(token)
        for schedule in unlockSchedules:
            console.log("get_distributed_in_range", schedule)
            geyserMock.add_unlock_schedule(token, schedule)

    tokenDistributions = geyserMock.calc_token_distributions_in_range(
        periodStartTime, periodEndTime
    )

    return tokenDistributions


def getExpectedDistributionInRange(badger: BadgerSystem, startBlock, endBlock):
    distributions = {}
    for key, geyser in badger.geysers.items():
        if key == "native.badger":
            dists = get_distributed_in_range(key, geyser, startBlock, endBlock)
            distributions[key] = dists

    console.log(distributions)

    # TODO: Only Badger for now
    totals = {}
    totals[DIGG] = 0
    totals[Token.badger.value] = 0

    for key, gains in distributions.items():
        totals[Token.badger.value] += gains[Token.badger.value]
        totals[DIGG] += gains[Token.digg.value]

    return totals


def sum_claims(claims):
    total = 0
    for user, claim in claims.items():
        total += int(claim["cumulativeAmounts"][0])
    return total


def sum_digg_claims(claims):
    total = 0
    for user, claim in claims.items():
        # print(claim["cumulativeAmounts"])
        total += int(claim["cumulativeAmounts"][1])
    return total


def diff_rewards(
    badger: BadgerSystem,
    before_file,
    after_file,
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
            [
                user,
                val(beforeClaim),
                val(afterClaim),
                val(diff),
                proportionGained,
            ]
        )
    print(
        tabulate(
            table,
            headers=["user", "a", "b", "diff", "% gained"],
        )
    )


def get_expected_total_rewards(periodEndTime):
    startTime = 1611489600
    timePassed = periodEndTime - startTime
    print("timePassed", timePassed)

    badger_base = Wei("4248761 ether")
    badger_per_day = Wei("184452 ether") // 7

    digg_base = Wei("45 gwei")
    digg_per_day = Wei("138.4 gwei") // 7

    return {
        "badger": badger_base + (badger_per_day * timePassed // days(1)),
        "digg": digg_base + (digg_per_day * timePassed // days(1)),
    }


def print_token_diff_table(name, before, after, sanity_diff, decimals=18):
    diff = after - before

    console.print("Diff for {}".format(name))
    table = []
    table.append(["{} before".format(name), val(before, decimals=decimals)])
    table.append(["{} after".format(name), val(after, decimals=decimals)])
    table.append(["{} diff".format(name), val(diff, decimals=decimals)])
    print(tabulate(table, headers=["key", "value"]))

    assert diff <= sanity_diff


def verify_rewards(badger: BadgerSystem, startBlock, endBlock, before_data, after_data):
    before = before_data["claims"]
    after = after_data["claims"]

    print(startBlock, endBlock)

    periodStartTime = web3.eth.getBlock(int(startBlock))["timestamp"]
    periodEndTime = web3.eth.getBlock(int(endBlock))["timestamp"]

    digg_contract = get_digg_contract()
    spf = digg_contract._initialSharesPerFragment()

    expected_totals = get_expected_total_rewards(periodEndTime)

    sanity_badger = expected_totals["badger"]
    sanity_digg = expected_totals["digg"] * digg_contract._initialSharesPerFragment()
    total_before_badger = int(before_data["tokenTotals"].get(BADGER, 0))
    total_after_badger = int(after_data["tokenTotals"].get(BADGER, 0))
    total_before_digg = int(before_data["tokenTotals"].get(DIGG, 0))
    total_after_digg = int(after_data["tokenTotals"].get(DIGG, 0))

    diff_badger = total_after_badger - total_before_badger
    diff_digg = total_after_digg - total_before_digg

    table = []
    table.append(["block range", startBlock, endBlock])
    table.append(["block duration", int(endBlock) - int(startBlock), "-"])
    table.append(["duration", hours(periodEndTime - periodStartTime), "-"])
    table.append(["badger before", val(total_before_badger), "-"])
    table.append(["badger after", val(total_after_badger), "-"])
    table.append(["badger diff", val(diff_badger), "-"])
    table.append(["badger sanity ", val(sanity_badger), "-"])
    table.append(["digg before", val(total_before_digg // spf, decimals=9), "-"])
    table.append(["digg after", val(total_after_digg // spf, decimals=9), "-"])
    table.append(["digg diff", val(diff_digg // spf, decimals=9), "-"])
    table.append(["digg sanity", val(sanity_digg // spf, decimals=9), "-"])

    print(tabulate(table, headers=["key", "value", "scaled"]))

    for name, token in TOKENS_TO_CHECK.items():
        if name in ["Digg", "Badger"]:
            continue
        total_before_token = int(before_data["tokenTotals"].get(token, 0))
        total_after_token = int(after_data["tokenTotals"].get(token, 0))
        print_token_diff_table(
            name, total_before_token, total_after_token, 20000 * 1e18
        )

    assert total_after_digg < sanity_digg
    assert total_after_badger < sanity_badger


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

    root = badger.badgerTree.merkleRoot()
    contentHash = badger.badgerTree.merkleContentHash()
    lastUpdateTime = badger.badgerTree.lastPublishTimestamp()
    blockNumber = badger.badgerTree.lastPublishBlockNumber()

    expectedContentHash = str(contentHash)

    assert beforeContentHash == expectedContentHash

    periodStartTime = web3.eth.getBlock(startBlock)["timestamp"]
    periodEndTime = web3.eth.getBlock(endBlock)["timestamp"]

    duration = periodEndTime - periodStartTime

    print("duration: ", duration)

    # Expected gains must match up with the distributions from various rewards programs
    expectedGains = getExpectedDistributionInRange(badger, startBlock, endBlock)

    # Total claims must only increase
    sum_before = sum_claims(before)
    sum_after = sum_claims(after)
    sanitySum = Wei("5000000 ether")

    sum_digg_after = sum_digg_claims(after)
    digg_contract = interface.IDigg(DIGG)

    table = []
    table.append(["block range", startBlock, endBlock])
    table.append(["duration", periodEndTime - periodStartTime, "-"])
    table.append(["sum before", sum_before, val(sum_before)])
    table.append(["sum after", sum_after, val(sum_after)])
    table.append(["digg shares after", sum_digg_after, val(sum_digg_after)])
    table.append(
        [
            "digg tokens after",
            digg_contract.sharesToFragments(sum_digg_after),
            val(digg_contract.sharesToFragments(sum_digg_after)),
        ]
    )
    table.append(
        [
            "From last period",
            sum_after - sum_before,
            val(sum_after - sum_before),
        ]
    )
    table.append(
        [
            "Sanity Sum",
            sanitySum,
            "-",
        ]
    )
    print(tabulate(table, headers=["key", "value", "scaled"]))

    assert sum_after >= sum_before
    assert sum_after <= sanitySum
    # assert sum_after - (sum_before + expectedGains[Token.badger]) < 10000
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
            [
                user,
                val(beforeClaim),
                val(afterClaim),
                val(diff),
                proportionGained,
            ]
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
        after_file["startBlock"],
        after_file["endBlock"],
        {"from": badger.keeper, "gas_price": gas_strategy},
    ),

    time.sleep(15)

    badger.badgerTree.approveRoot(
        after_file["merkleRoot"],
        afterContentHash,
        after_file["cycle"],
        after_file["startBlock"],
        after_file["endBlock"],
        {"from": badger.guardian, "gas_price": gas_strategy},
    ),


def test_claims(badger: BadgerSystem, startBlock, endBlock, before_file, after_file):
    before = before_file["claims"]
    claims = after_file["claims"]

    digg = connect_digg("deploy-final.json")

    # Total claims must only increase
    total_claimable = sum_claims(claims)

    table = []
    # Each users' cumulative claims must only increase
    total_claimed = 0
    users = [
        web3.toChecksumAddress("0x302218182415dc9800179f50a8b16ff98b8d04c3"),
        web3.toChecksumAddress("0xbc159b71c296c21a1895a8ddf0aa45969c5f17c2"),
        web3.toChecksumAddress("0x264571c538137922c6e8aF4927C3D3F681399E50"),
        web3.toChecksumAddress("0x57ef012861c4937a76b5d6061be800199a2b9100"),
    ]
    for user, claim in claims.items():
        if not user in users:
            continue

        claimed = badger.badgerTree.getClaimedFor(user, [badger.token.address])[1][0]
        claimed_digg = badger.badgerTree.getClaimedFor(user, [digg.token.address])[1][0]

        badger_claimable = int(claim["cumulativeAmounts"][0])
        digg_claimable = int(claim["cumulativeAmounts"][1])

        badger_diff = badger_claimable - claimed
        digg_diff = digg_claimable - claimed_digg

        print("=== Claim: " + user + " ===")

        console.print(
            {
                "user": user,
                "badger_claimed": val(claimed),
                "badger_claimable": val(badger_claimable),
                "badger_diff": val(badger_diff),
                "digg_claimed": claimed_digg,
                "digg_claimable": digg_claimable,
                "digg_diff": digg_diff,
                "digg_claimed_scaled": val(
                    digg_contract.sharesToFragments(claimed_digg), decimals=9
                ),
                "digg_claimable_scaled": val(
                    digg_contract.sharesToFragments(digg_claimable), decimals=9
                ),
                "digg_diff_scaled": val(
                    digg_contract.sharesToFragments(digg_diff), decimals=9
                ),
            }
        )

        accounts[0].transfer(user, Wei("0.5 ether"))
        accounts.at(user, force=True)

        pre = badger.token.balanceOf(user)
        pre_digg = digg.token.balanceOf(user)
        pre_digg_shares = digg.token.sharesOf(user)

        tx = badger.badgerTree.claim(
            claim["tokens"],
            claim["cumulativeAmounts"],
            claim["index"],
            claim["cycle"],
            claim["proof"],
            {"from": user, "allow_revert": True},
        )

        # tx = badger.badgerTree.claim(
        #     claim["tokens"],
        #     claim["cumulativeAmounts"],
        #     claim["index"],
        #     claim["cycle"],
        #     claim["proof"],
        #     {"from": user, "allow_revert": True},
        # )

        print(tx.events)

        post = badger.token.balanceOf(user)
        post_digg = digg.token.balanceOf(user)
        post_digg_shares = digg.token.sharesOf(user)

        diff = post - pre
        table.append([user, "badger", pre, post, diff, claim["cumulativeAmounts"][0]])

        table.append(
            [
                user,
                "digg shares",
                pre_digg_shares,
                post_digg_shares,
                post_digg_shares - pre_digg_shares,
                claim["cumulativeAmounts"][1],
            ]
        )

        table.append([user, "digg tokens", pre_digg, post_digg, "", ""])
        print(
            tabulate(
                table, headers=["user", "token", "before", "after", "diff", "claim"]
            )
        )

        total_claimed += int(claim["cumulativeAmounts"][0])

        assert post == pre + (int(claim["cumulativeAmounts"][0]) - claimed)
        assert (
            post_digg_shares
            - (pre_digg_shares + (int(claim["cumulativeAmounts"][1]) - claimed_digg))
            < 10 ** 18
        )

    print(total_claimable, total_claimed, total_claimable - total_claimed)
