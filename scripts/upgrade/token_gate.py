from helpers.time_utils import days
from ape_safe import ApeSafe
from brownie import *
from helpers.constants import *
from eth_abi import encode_abi
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from config.badger_config import badger_config, digg_config, sett_config
from helpers.registry import artifacts
from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console
from helpers.registry import registry

def main():
    badger = connect_badger()

    if rpc.is_active():
        dev_multi = ApeSafe(badger.testMultisig.address)
        helper = ApeSafeHelper(badger, dev_multi)
    else:
        from helpers.gas_utils import gas_strategies
        gas_strategies.set_default(gas_strategies.exponentialScalingFast)

    # Deploy logic
    logic = GatedMiniMeController.deploy({"from": badger.deployer})
    logic.initialize(badger.token)

    # Deploy proxy

    # Create Aragon Vote

    # Execute Aragon Vote
    # badger.voteWithSystemContracts(voteId)

    helper.publish()