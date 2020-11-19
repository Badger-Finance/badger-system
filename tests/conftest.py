from helpers.proxy_utils import deploy_proxy
import pytest
from operator import itemgetter
from brownie.test import given, strategy
from brownie import *
from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from dotmap import DotMap
from scripts.deploy.deploy_badger import main
from helpers.registry import whale_registry


@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    # perform a chain rewind after completing each test, to ensure proper isolation
    # https://eth-brownie.readthedocs.io/en/v1.10.3/tests-pytest-intro.html#isolation-fixtures
    pass


@pytest.fixture()
def badger(accounts):
    badger_system = main()

    # Distribute Test Assets

    return badger_system


def distribute_rewards_escrow(badger, token, recipient, amount):
    """
    Distribute Badger from rewardsEscrow
    """

    # Approve recipient for expenditure
    if not badger.rewardsEscrow.isApproved(recipient):
        exec_direct(
            badger.devMultisig,
            {
                "to": badger.rewardsEscrow,
                "data": badger.rewardsEscrow.approveRecipient.encode_input(recipient),
            },
            badger.deployer,
        )

    exec_direct(
        badger.devMultisig,
        {
            "to": badger.rewardsEscrow,
            "data": badger.rewardsEscrow.transfer.encode_input(
                token, recipient, amount
            ),
        },
        badger.deployer,
    )



