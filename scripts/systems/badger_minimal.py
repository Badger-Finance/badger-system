import json
from scripts.systems.badger_system import BadgerSystem
from scripts.systems.gnosis_safe_system import connect_gnosis_safe
from helpers.time_utils import days
from helpers.proxy_utils import deploy_proxy, deploy_proxy_admin
from brownie import *
from helpers.constants import AddressZero, EmptyBytes32
from helpers.registry import registry
from dotmap import DotMap
from config.badger_config import badger_config, sett_config, badger_total_supply


def deploy_badger_minimal(deployer, keeper=None, guardian=None):

    if not keeper:
        keeper = deployer
    if not guardian:
        guardian = deployer
    badger = BadgerSystem(
        badger_config, deployer=deployer, keeper=keeper, guardian=guardian
    )

    badger.deploy_sett_core_logic()
    badger.deploy_logic("RewardsEscrow", RewardsEscrow)
    badger.deploy_logic("BadgerTree", BadgerTree)
    badger.deploy_rewards_escrow()
    badger.deploy_badger_tree()

    return badger
