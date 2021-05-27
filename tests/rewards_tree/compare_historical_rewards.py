import json
import secrets
import pytest
from helpers.constants import *
from helpers.registry import registry
from rich.console import Console

from scripts.rewards.rewards_utils import calc_next_cycle_range
from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from assistant.rewards.aws_utils import download_past_trees
from assistant.rewards.rewards_assistant import run_action


console = Console()


@pytest.fixture(scope="function", autouse="True")
def setup():
    trees = download_past_trees(2)
    pastRewards = json.load(trees[1])
    lastTree = json.loads(trees[0])

    badger = connect_badger(
        badger_config.prod_json, load_keeper=False, load_deployer=False
    )
    startBlock = int(lastTree["startBlock"])
    endBlock = int(lastTree["endBlock"])

    newTree = run_action(
        badger,
        {
            "action": "rootUpdater",
            "startBlock": startBlock,
            "endBlock": endBlock,
            "pastRewards": pastRewards,
        },
        test=True,
    )["merkleTree"]
    return (lastTree, newTree)


def test_compare_tree(setup):
    lastTree = setup[0]
    newTree = setup[1]
    console.log(lastTree["merkleRoot"])
    console.log(newTree["merkleRoot"])
