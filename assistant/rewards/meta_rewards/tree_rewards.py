from assistant.subgraph.client import fetch_tree_distributions
from assistant.rewards.rewards_utils import calculate_sett_balances
from rich.console import Console
from assistant.rewards.classes.RewardsList import RewardsList
console = Console()

def calc_tree_rewards(badger,startBlock,endBlock,nextCycle):
    treeDists = fetch_tree_distributions(startBlock,endBlock)
    console.log("Calculating rewards for {} harvests between {} and {}".format(
        len(treeDists),
        startBlock,
        endBlock
    ))
    rewards = RewardsList(nextCycle,badger.badgerTree)
    rewardsData = {}
    for dist in treeDists:
        blockNumber = dist["blockNumber"]
        strategy = dist["id"].split("-")[0]
        token = dist["token"]["address"]
        symbol = dist["token"]["symbol"]
        amountToDistribute = int(dist["amount"])

        console.log("Processing harvest...")
        console.log("Token:{}".format(symbol))
        console.log("Amount:{} \n".format(amountToDistribute/1e18))

        if symbol not in rewardsData:
            rewardsData[symbol] = 0

        rewardsData[symbol] += amountToDistribute
        settName = badger.getSettFromStrategy(strategy)
        balances = calculate_sett_balances(badger,settName,int(blockNumber))
        totalBalance = sum([u.balance for u in balances])
        rewardsUnit = amountToDistribute/totalBalance
        for user in balances:
            userReward = rewardsUnit * user.balance
            rewards.increase_user_rewards(user.address,token,int(userReward))

    console.log(rewardsData)

    return rewards


        
    # match to vaults
    # query vaults at endblock
    # calc rewards