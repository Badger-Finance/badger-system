from tqdm import tqdm
from brownie import *
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.rewards_utils import calculate_sett_balances
from rich.console import Console

console = Console()


def calc_rewards(badger, start, end, nextCycle, events, name, token):
    def filter_events(e):
        return int(e["blockNumber"]) > start and int(e["blockNumber"]) < end
    filteredEvents = list(filter(filter_events, events))
    rewards = RewardsList(nextCycle, badger.badgerTree)
    if len(filteredEvents) > 0:
        console.log(filteredEvents)
        console.log("{} events to process for {}".format(len(filteredEvents), name))
        rewards = process_rewards(badger, filteredEvents, name, nextCycle, token)
    else:
        console.log("No events to process for {}".format(name))
    return rewards


def process_rewards(badger, events, name, nextCycle, token):
    totalFromEvents = sum([int(e["rewardAmount"]) for e in events]) / 1e18
    rewards = RewardsList(nextCycle, badger.badgerTree)
    total = 0
    for event in events:
        userState = calc_meta_farm_rewards(badger, name, event["blockNumber"])
        totalBalance = sum([u.balance for u in userState])
        total += int(event["rewardAmount"])
        console.log("{} total {} processed".format(total / 1e18, token))
        rewardsUnit = int(event["rewardAmount"]) / totalBalance
        for user in userState:
            rewards.increase_user_rewards(
                web3.toChecksumAddress(user.address),
                web3.toChecksumAddress(token),
                rewardsUnit * user.balance,
            )

    totalFromRewards = sum(
        [list(v.values())[0] / 1e18 for v in list(rewards.claims.values())]
    )

    # Calc diff of rewardsTotal and add assertion for checking rewards
    rewardsDiff = abs(totalFromRewards - totalFromRewards) * 1e18
    console.log(
        "Total from Rewards: {} \nTotal from Events: {}\n Diff: {}".format(
            totalFromRewards, totalFromEvents, rewardsDiff
        )
    )
    if abs(totalFromEvents - totalFromRewards) > 100000:
        assert False, "Incorrect total rewards"

    return rewards


def calc_meta_farm_rewards(badger, name, harvestBlock):
    console.log("Calculating rewards for {} harvest at {}".format(name, harvestBlock))
    harvestBlock = int(harvestBlock)
    sett = badger.getSett(name)
    balances = calculate_sett_balances(badger, name, harvestBlock)
    return balances
