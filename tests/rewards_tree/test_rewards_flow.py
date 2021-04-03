import json
import secrets

import brownie
import pytest
from assistant.rewards import rewards_assistant
from brownie import *
from helpers.constants import *
from helpers.registry import registry
from rich.console import Console

console = Console()


@pytest.fixture(scope="function", autouse="True")
def setup(rewards_tree_unit):
    return rewards_tree_unit


@pytest.fixture(scope="function")
def setup_badger(badger_tree_unit):
    return badger_tree_unit


# @pytest.mark.skip()
def test_rewards_flow(setup):
    # Propose root

    # Test variations of invalid data upload and verify revert string

    # Ensure event

    # Approve root

    # Test variations of invalid data upload and verify revert string

    # Ensure event

    # Claim as a user

    # Update to new root with xSushi and FARM

    # Claim as user who has xSushi and FARM

    # Ensure tokens are as expected

    # Claim partial as a user

    # Try to claim with zero tokens all around, expect failure
    pass
