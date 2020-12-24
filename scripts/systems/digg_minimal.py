from scripts.systems.digg_system import DiggSystem
from config.badger_config import digg_config
from scripts.systems.sett_system import deploy_sett_system


def deploy_digg_minimal(deployer, devProxyAdmin, daoProxyAdmin, owner=None):

    badger = DiggSystem(digg_config, None, deployer, keeper, guardian)

    badger.deploy_sett_core_logic()
    badger.deploy_logic("RewardsEscrow", RewardsEscrow)
    badger.deploy_logic("BadgerTree", BadgerTree)
    badger.deploy_rewards_escrow()
    badger.deploy_badger_tree()

    return badger
