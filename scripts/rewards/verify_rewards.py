from brownie.network.gas.strategies import GasNowStrategy
from helpers.constants import (
    DEFAULT_ADMIN_ROLE,
    PAUSER_ROLE,
    ROOT_PROPOSER_ROLE,
    ROOT_VALIDATOR_ROLE,
    UNPAUSER_ROLE,
)
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
import json
from assistant.rewards.rewards_checker import push_rewards, test_claims, verify_rewards
from scripts.rewards.rewards_utils import calc_next_cycle_range
import time

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger

from assistant.rewards.rewards_assistant import (
    fetch_current_rewards_tree,
    fetch_pending_rewards_tree,
    run_action,
)

console = Console()

gas_strategy = GasNowStrategy("rapid")


def test_main():
    main()


def main():
    badger = connect_badger(
        badger_config.prod_json, load_keeper=True, load_guardian=True
    )
    pendingContentHash = (
        "0x346ec98585b52d981d43584477e1b831ce32165cb8e0a06d14d236241b36328e"
    )
    pendingFile = "rewards-1-" + str(pendingContentHash) + ".json"
    with open(pendingFile) as f:
        after_file = json.load(f)

    pendingRewards = after_file
    # pendingRewards = fetch_current_rewards_tree(badger)
    currentRewards = fetch_current_rewards_tree(badger)

    accounts[0].transfer(badger.keeper, Wei("5 ether"))
    accounts[0].transfer(badger.guardian, Wei("5 ether"))

    # Upgrade Rewards Tree
    multi = GnosisSafe(badger.devMultisig)

    newLogic = BadgerTree.at("0x0f81D3f48Fedb8E67a5b87A8a4De57766157f19B")

    multi.execute(
        MultisigTxMetadata(
            description="Upgrade Tree",
        ),
        {
            "to": badger.opsProxyAdmin.address,
            "data": badger.opsProxyAdmin.upgrade.encode_input(
                badger.badgerTree, newLogic
            ),
        },
    )

    assert (
        badger.badgerTree.hasRole(DEFAULT_ADMIN_ROLE, badger.devMultisig.address)
        == True
    )
    assert badger.badgerTree.getRoleMemberCount(DEFAULT_ADMIN_ROLE) == 1

    assert badger.badgerTree.hasRole(ROOT_PROPOSER_ROLE, badger.keeper.address) == True
    assert badger.badgerTree.getRoleMemberCount(ROOT_PROPOSER_ROLE) == 1

    # assert badger.badgerTree.hasRole(ROOT_VALIDATOR_ROLE, badger.guardian.address) == True
    # assert badger.badgerTree.getRoleMemberCount(ROOT_VALIDATOR_ROLE) == 1

    assert badger.badgerTree.hasRole(PAUSER_ROLE, badger.guardian.address) == True
    assert badger.badgerTree.getRoleMemberCount(PAUSER_ROLE) == 1

    assert badger.badgerTree.hasRole(UNPAUSER_ROLE, badger.devMultisig.address) == True
    assert badger.badgerTree.getRoleMemberCount(UNPAUSER_ROLE) == 1

    verify_rewards(
        badger,
        pendingRewards["startBlock"],
        pendingRewards["endBlock"],
        currentRewards,
        pendingRewards,
    )
    # push_rewards(badger, pendingContentHash)

    # if rpc.is_active():
    #     test_claims(badger, pendingRewards["startBlock"], pendingRewards["endBlock"], currentRewards, pendingRewards)
