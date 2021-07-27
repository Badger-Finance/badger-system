from helpers.constants import PEAK_ADDRESSES
from assistant.subgraph.client import fetch_tree_distributions
from assistant.subgraph.client import fetch_wallet_balances
from scripts.systems.badger_system import BadgerSystem
from assistant.rewards.rewards_utils import calculate_sett_balances
from rich.console import Console
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.classes.RewardsLog import rewardsLog
from brownie import web3

console = Console()


def calc_tree_rewards(
    badger: BadgerSystem, startBlock: int, endBlock: int, nextCycle: int, chain: str
):
    """
    Calculate extra rewards based on TreeDistribution events as part of farm and distribute.
    """
    # sharesPerFragment = badger.digg.logic.UFragments._sharesPerFragment()
    # _, _2, ibbtc_balances = fetch_wallet_balances(sharesPerFragment, endBlock)

    treeDists = fetch_tree_distributions(startBlock, endBlock)
    console.log(
        "Calculating rewards for {} harvests between {} and {}".format(
            len(treeDists), startBlock, endBlock
        )
    )
    rewards = RewardsList(nextCycle, badger.badgerTree)
    rewardsData = {}
    for dist in treeDists:
        blockNumber = dist["blockNumber"]
        strategy = dist["id"].split("-")[0]
        token = dist["token"]["address"]
        symbol = dist["token"]["symbol"]
        amountToDistribute = int(dist["amount"])

        console.log("Processing harvest...")
        console.log("Token:{}".format(symbol))
        console.log("Amount:{} \n".format(amountToDistribute / 1e18))

        if symbol not in rewardsData:
            rewardsData[symbol] = 0

        rewardsData[symbol] += amountToDistribute / 1e18
        settName = badger.getSettFromStrategy(strategy)
        balances = calculate_sett_balances(badger, settName, int(blockNumber))
        totalBalance = sum([u.balance for u in balances])
        rewardsUnit = amountToDistribute / totalBalance
        rewardsLog.add_total_token_dist(
            settName, web3.toChecksumAddress(token), amountToDistribute / 1e18
        )
        # totalIbbtcBalance = sum(ibbtc_balances.values())
        for user in balances:
            userReward = rewardsUnit * user.balance
            # if user.address in [a.lower() for a in PEAK_ADDRESSES]:
            #     ibbtcRewardsUnit = userReward / totalIbbtcBalance

            #     console.log(
            #         "Distributing {} {} to {} ibbtc holders from {}".format(
            #             userReward / 1e18, symbol, len(ibbtc_balances), settName
            #         )
            #     )

            #     # Redistribute peak addresses rewards to ibbtc users
            #     for addr, balance in ibbtc_balances.items():

            #         rewards.increase_user_rewards(
            #             web3.toChecksumAddress(addr),
            #             token,
            #             int(ibbtcRewardsUnit * balance),
            #         )
            # else:
            rewards.increase_user_rewards(
                web3.toChecksumAddress(user.address),
                web3.toChecksumAddress(token),
                int(userReward),
            )

    console.log(rewardsData)

    return rewards
