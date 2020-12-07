"""
Early Contributor Program - Badger
5% of Badger supply to ECs
- Everyone gets 30% up front
- 70% over 12 weeks, weekly
"""

"""
Early Contributor Program - Digg
10% of Digg supply to ECs
- Everyone gets 30% up front
- 70% over 12 weeks, weekly
"""
import json
from assistant.rewards.RewardsList import RewardsList
from brownie import web3

def get_contributors():
    with open("merkle/early_contributors.json") as f:
        data = json.load(f)
        return data

def calc_early_contributor_rewards(badger, cycle):
    data = get_contributors()
    rewards = RewardsList(cycle=cycle, badgerTree=badger.badgerTree)

    # Initial Distribution: Amount from file * .3
    for key, value in data.items():
        
        wei = float(value) * 1e18
        # print(key, value, wei)
        data[key] = int(wei * 0.3)
        rewards.increase_user_rewards(web3.toChecksumAddress(key), badger.token.address, data[key])

    return rewards