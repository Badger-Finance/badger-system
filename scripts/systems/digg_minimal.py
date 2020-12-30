from scripts.systems.digg_system import DiggSystem
from config.badger_config import digg_config


def deploy_digg_minimal(deployer, devProxyAdmin, daoProxyAdmin, owner=None):

    digg = DiggSystem(digg_config, deployer, devProxyAdmin, daoProxyAdmin)

    digg.deploy_core_logic()
    digg.deploy_digg_token()
    digg.deploy_digg_policy()
    digg.deploy_orchestrator()
    digg.deploy_market_median_oracle()
    digg.deploy_cpi_median_oracle()
    digg.deploy_constant_oracle()
    digg.deploy_dynamic_oracle()

    return digg
