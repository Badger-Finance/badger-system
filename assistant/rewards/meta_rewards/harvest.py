from brownie import *
from assistant.subgraph.client import fetch_farm_harvest_events
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.meta_rewards.calc_meta_rewards import calc_rewards
from assistant.rewards.rewards_utils import combine_rewards

farmTokenAddress = "0xa0246c9032bC3A600820415aE600c6388619A14D"


def calc_farm_rewards(badger, startBlock, endBlock, nextCycle, retroactive):
    farmEvents = fetch_farm_harvest_events()

    return calc_rewards(
        badger,
        startBlock,
        endBlock,
        nextCycle,
        farmEvents,
        "harvest.renCrv",
        farmTokenAddress,
        retroactive=retroactive,
        retroactiveStart=11376266,
    )
