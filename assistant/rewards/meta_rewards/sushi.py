from brownie import *
from assistant.subgraph.client import fetch_sushi_harvest_events
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.meta_rewards.calc_meta_rewards import calc_rewards
from assistant.rewards.rewards_utils import combine_rewards

xSushiTokenAddress = "0x8798249c2e607446efb7ad49ec89dd1865ff4272"


def calc_all_sushi_rewards(badger, startBlock, endBlock, nextCycle, retroactive):
    allSushiEvents = fetch_sushi_harvest_events()

    wbtcEthRewards = calc_sushi_rewards(
        badger,
        startBlock,
        endBlock,
        nextCycle,
        allSushiEvents["wbtcEth"],
        "native.sushiWbtcEth",
        retroactive=retroactive,
        retroactiveStart=11537600,
    )
    wbtcBadgerRewards = calc_sushi_rewards(
        badger,
        startBlock,
        endBlock,
        nextCycle,
        allSushiEvents["wbtcBadger"],
        "native.sushiBadgerWbtc",
        retroactive=retroactive,
        retroactiveStart=11539529,
    )
    wbtcDiggRewards = calc_sushi_rewards(
        badger,
        startBlock,
        endBlock,
        nextCycle,
        allSushiEvents["wbtcDigg"],
        "native.sushiDiggWbtc",
        retroactive=retroactive,
        retroactiveStart=11676338,
    )
    # Verify all rewards are correct (for extra safety)
    return combine_rewards(
        [wbtcEthRewards, wbtcBadgerRewards, wbtcDiggRewards],
        nextCycle,
        badger.badgerTree,
    )


def calc_sushi_rewards(
    badger, startBlock, endBlock, nextCycle, events, name, retroactive, retroactiveStart
):
    return calc_rewards(
        badger,
        startBlock,
        endBlock,
        nextCycle,
        events,
        name,
        xSushiTokenAddress,
        retroactive=retroactive,
        retroactiveStart=retroactiveStart,
    )
