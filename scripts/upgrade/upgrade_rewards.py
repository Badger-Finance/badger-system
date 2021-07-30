"""
  Script to pass governance rewards to multisig
"""
from rich.console import Console

from config.badger_config import badger_config
from scripts.systems.badger_system import BadgerSystem, connect_badger
from helpers.time_utils import days, to_days, to_utc_date
from eth_abi import encode_abi
from brownie import *


console = Console()

## Change these to customize functionality
CONTROLLER_ADDRESS = "0x63cF44B2548e4493Fd099222A1eC79F3344D9682"
GOVERNANCE_MULTISIG_ADDRESS = "0xB65cef03b9B89f99517643226d76e286ee999e77"
FUNCTION_TO_CALL = "setRewards(address)"


def test_update_rewards(badger: BadgerSystem) -> str:
    data = encode_abi(["address"], [GOVERNANCE_MULTISIG_ADDRESS])
    delay = 2 * days(2)
    eta = web3.eth.getBlock("latest")["timestamp"] + delay

    result = badger.timelock_run_direct(CONTROLLER_ADDRESS, FUNCTION_TO_CALL, data, eta)

    controller = badger.getController("native")
    assert controller.rewards() == GOVERNANCE_MULTISIG_ADDRESS
    console.print(
        "[orange] Controller Rewards {} [/orange]".format(controller.rewards())
    )
    return result


def update_rewards(badger: BadgerSystem) -> str:
    data = encode_abi(["address"], [GOVERNANCE_MULTISIG_ADDRESS])
    delay = 2 * days(2)
    eta = web3.eth.getBlock("latest")["timestamp"] + delay

    return badger.governance_queue_transaction(
        CONTROLLER_ADDRESS, FUNCTION_TO_CALL, data, eta
    )


def main():
    """
    Queue Update of Controller.rewards for 0x63cF44B2548e4493Fd099222A1eC79F3344D9682
    """
    badger = connect_badger(badger_config.prod_json)

    ## test_update_rewards(badger)
    update_rewards(badger)
