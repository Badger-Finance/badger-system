import json

from eth_utils.hexadecimal import encode_hex

from assistant.rewards.calc_stakes import calc_geyser_stakes
from assistant.rewards.config import config
from assistant.rewards.merkle_tree import rewards_to_merkle_tree
from brownie import *
from dotmap import DotMap
from helpers.constants import EmptyBytes32, GUARDIAN_ROLE
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from eth_abi.packed import encode_abi_packed

console = Console()


class RewardsList:
    def __init__(self, cycle) -> None:
        self.claims = DotMap()
        self.tokens = DotMap()
        self.totals = DotMap()
        self.cycle = cycle

    def increase_user_rewards(self, user, token, toAdd):
        """
        If user has rewards, increase. If not, set their rewards to this initial value
        """
        if user in self.claims and token in self.claims[user]:
            self.claims[user][token] += toAdd
        else:
            self.claims[user][token] = toAdd

        if token in self.totals:
            self.totals[token] += toAdd
        else:
            self.totals[token] = toAdd

    def printState(self):
        console.log("claims", self.claims.toDict())
        console.log("tokens", self.tokens.toDict())
        console.log("cycle", self.cycle)

    def hasToken(self, token):
        if self.tokens[token]:
            return self.tokens[token]
        else:
            return False

    def getTokenRewards(self, user, token):
        if self.claims[user][token]:
            return self.claims[user][token]
        else:
            return 0

    def to_node_entry(self, user, userData, cycle, index):
        nodeEntry = {
            "user": user,
            "tokens": [],
            "cumulativeAmounts": [],
            "cycle": cycle,
            "index": index,
        }
        for tokenAddress, cumulativeAmount in userData.items():
            nodeEntry["tokens"].append(tokenAddress)
            nodeEntry["cumulativeAmounts"].append(cumulativeAmount)

        encoded = encode_hex(
            encode_abi_packed(
                ["uint", "address", "uint", "address[]", "uint[]"],
                (
                    nodeEntry["index"],
                    nodeEntry["user"],
                    nodeEntry["cycle"],
                    nodeEntry["tokens"],
                    nodeEntry["cumulativeAmounts"],
                ),
            )
        )

        console.log('nodeEntry', nodeEntry)
        console.log('encoded', encoded)
        return (nodeEntry, encoded)

    def to_merkle_format(self):
        """
        - Sort users into alphabetical order
        - Node entry = [cycle, user, index, token[], cumulativeAmount[]]
        """
        cycle = self.cycle
        dict = self.claims.toDict()

        nodeEntries = []
        encodedEntries = []

        index = 0

        for user, userData in self.claims.items():
            (nodeEntry, encoded) = self.to_node_entry(user, userData, cycle, index)
            nodeEntries.append(nodeEntry)
            encodedEntries.append(encoded)
            index += 1

        return (nodeEntries, encodedEntries)


def sum_rewards(rewardsList, cycle):
    """
    Sum rewards from all given set of rewards' list, returning a single rewards list
    """
    totals = RewardsList(cycle)

    # For each rewards list entry
    for key, rewardsSet in rewardsList.items():
        # Get the claims data
        claims = rewardsSet["claims"]
        for user, userData in claims.items():
            # For each token
            for token, tokenAmount in userData.items():
                totals.increase_user_rewards(user, token, tokenAmount)
    totals.printState()
    return totals


def calc_geyser_rewards(badger, startBlock, endBlock, cycle):
    rewardsByGeyser = {}

    # For each Geyser, get a list of user to weights
    for key, geyser in badger.geysers.items():
        geyserRewards = calc_geyser_stakes(
            geyser, badger.globalStartBlock, startBlock, endBlock
        )
        rewardsByGeyser[key] = geyserRewards

    console.log("rewardsByGeyser", rewardsByGeyser)
    


    return sum_rewards(rewardsByGeyser, cycle)


def calc_harvest_meta_farm_rewards(badger, startBlock, endBlock):
    # TODO: Add harvest rewards
    return RewardsList()


def calc_early_contributor_rewards(badger, startBlock, endBlock):
    # TODO: Add earky contributor rewards
    return False


def guardian(badger, endBlock):
    """
    Guardian Role
    - Check if there is a new proposed root
    - If there is, run the rewards script at the same block height to verify the results
    - If there is a discrepency, notify admin

    (In case of a one-off failure, Script will be attempted again at the guardianInterval)
    """
    badgerTree = badger.badgerTree
    guardian = badgerTree.getRoleMember(GUARDIAN_ROLE, 0)
    # TODO prod: accounts.add(private_key=ENV Variable)
    assert guardian == badger.guardian

    # Check latest root proposal
    proposed = badgerTree.getPendingMerkleData()
    nextCycle = badgerTree.currentCycle() + 1

    badger.badgerTree.approveRoot(proposed[0], proposed[1], nextCycle, {'from': guardian})
    chain.mine()


def rootUpdater(badger, endBlock):
    """
    Root Updater Role
    - Check how much time has passed since the last published update
    - If sufficient time has passed, run the rewards script and p
    - If there is a discrepency, notify admin

    (In case of a one-off failure, Script will be attempted again at the rootUpdaterInterval)
    """
    badgerTree = badger.badgerTree
    keeper = badger.keeper
    guardian = badger.guardian
    currentMerkleData = badgerTree.getCurrentMerkleData()
    nextCycle = badgerTree.currentCycle() + 1

    console.print("\n[bold cyan]===== Root Updater =====[/bold cyan]\n")

    console.log("currentMerkleData", currentMerkleData)
    timestamp = currentMerkleData[2]
    blockNumber = currentMerkleData[3]

    # Start after the previous snapshot, or globalStartBlock
    startBlock = max(badger.globalStartBlock, blockNumber + 1)

    geyserRewards = calc_geyser_rewards(badger, startBlock, endBlock, nextCycle)
    # metaFarmRewards = calc_harvest_meta_farm_rewards(badger, startBlock, endBlock)
    # earlyContributorRewards = calc_early_contributor_rewards(badger, startBlock, endBlock)

    totalRewards = geyserRewards
    merkleTree = rewards_to_merkle_tree(totalRewards)

    # Publish data
    badger.badgerTree.proposeRoot(merkleTree['merkleRoot'], EmptyBytes32, merkleTree['cycle'], {'from': keeper})
    chain.mine()
    

    with open("merkle-test.json", "w") as outfile:
        json.dump(merkleTree, outfile)
    return totalRewards


def watchdog(badger, endBlock):
    """
    Watchdog
    Ensure that the root has been updated within the maximum interval
    If not, the system is not functioning properly, notify admin
    """
    return False


def run_action(badger, args):
    if args["action"] == "rootUpdater":
        return rootUpdater(badger, args["endBlock"])
    if args["action"] == "guardian":
        return guardian(badger, args["endBlock"])
    if args["action"] == "watchdog":
        return watchdog(badger)
    return False


def main(args):
    # Load Badger system from config
    badger = connect_badger("local.json")

    # Attempt node connection.
    # If primary fails, try the backup
    # If backup fails, notify admin
    # Script will be run again at the defined interval

    # Determine start block and end block
    # Start block = Min(globalStartBlock, lastUpdateBlock+1)
    # If ETH block height < startBlock, fail

    # run_action(badger, args)

    # merkle_allocations = DotMap()

    # # Determine how many tokens of each type should be distributed during this time / block interval using unlockSchedules from all

    # pools = [
    #     badger.pools.sett.native.renCrv,
    #     badger.pools.sett.native.sbtcCrv,
    #     badger.pools.sett.native.tbtcCrv,
    #     badger.pools.sett.pickle.renCrv,
    #     badger.pools.sett.harvest.renCrv,
    # ]

    # for geyser in pools:
    #     distributions = calc_geyser_distributions(geyser, startBlock, endBlock)
    #     stakeWeights = calc_geyser_stakes(
    #         geyser, config.globalStartBlock, startBlock, endBlock
    #     )
    #     allocations = add_allocations(distributions, stakeWeights)

    # Confirm that totals don't exceed the expected - one safeguard against expensive invalid roots on the non-contract side
