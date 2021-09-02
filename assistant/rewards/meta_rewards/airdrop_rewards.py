import json
from helpers.constants import PEAK_ADDRESSES
from rich.console import Console
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.classes.RewardsLog import rewardsLog
from brownie import web3, Wei
from helpers.token_utils import val

console = Console()

AIRDROP_TOKEN_ADDRESS = web3.toChecksumAddress(
    "0x7e7E112A68d8D2E221E11047a72fFC1065c38e1a"
)


def fetch_airdrop(filename):
    with open(filename) as f:
        data = json.load(f)

    return data


def process_airdrop(airdrop_data):
    output = {}
    total = 0
    for address, amount in airdrop_data.items():
        amount_formatted = Wei(amount + " ether")
        output[address] = amount_formatted
        total += amount_formatted

        print(address, val(amount_formatted))

    return (output, total)


def calc_airdrop_rewards(badger, nextCycle):
    raw_data = fetch_airdrop("airdrop/bdigg-airdrop.json")
    (airdrop, total) = process_airdrop(raw_data)

    console.log(
        f"Pushing Airdrop of token {AIRDROP_TOKEN_ADDRESS} to {len(airdrop.items())} accounts with a total value of {val(total)}"
    )
    rewards = RewardsList(nextCycle, badger.badgerTree)
    rewardsData = {}
    for address, amount in airdrop.items():
        rewards.increase_user_rewards(
            web3.toChecksumAddress(address),
            web3.toChecksumAddress(AIRDROP_TOKEN_ADDRESS),
            int(amount),
        )

    console.log(rewardsData)
    return rewards
