from assistant.subgraph.client import fetch_tree_distributions
from assistant.badger_api.account import fetch_claimable_balances
from helpers.constants import BCVX, BCVXCRV
from rich.console import Console
from assistant.rewards.classes.RewardsList import RewardsList
from brownie import web3

console = Console()


def get_unclaimed_rewards(addresses):
    console.log("Fetching {} unclaimed balances".format(len(addresses)))
    chunked = chunk(addresses, 500)
    bCvxClaimable = {}
    bCvxCrvClaimable = {}
    for c in chunked:
        claimable_balances = fetch_claimable_balances(c)
        console.log("Queried {} claims".format(len(claimable_balances)))

        for addr, cb in claimable_balances.items():
            for c in cb:
                if c["address"] == BCVX:
                    bCvxClaimable[addr] = int(c["balance"])
                if c["address"] == BCVXCRV:
                    bCvxCrvClaimable[addr] = int(c["balance"])

    return {"bCvx": bCvxClaimable, "bCvxCrv": bCvxCrvClaimable}


def chunk(l, n):
    n = max(1, n)
    return (l[i : i + n] for i in range(0, len(l), n))
