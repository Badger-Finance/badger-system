from brownie import chain

from scripts.systems.digg_system import DiggSystem
from config.badger_config import digg_config_test


def deploy_digg_minimal(deployer, devProxyAdmin, daoProxyAdmin, owner=None):

    digg = DiggSystem(
        digg_config_test, deployer, devProxyAdmin, daoProxyAdmin, owner=deployer
    )

    deployer = digg.deployer

    digg.deploy_core_logic()
    digg.deploy_digg_token()
    digg.deploy_digg_policy()
    digg.deploy_orchestrator()
    digg.deploy_market_median_oracle()
    digg.deploy_cpi_median_oracle()
    digg.deploy_constant_oracle()

    digg.deploy_dao_digg_timelock()
    digg.deploy_digg_team_vesting()

    print("deploy_digg_minimal", deployer)

    # Setup constant oracle as provider to cpi median oracle.
    digg.cpiMedianOracle.addProvider(
        digg.constantOracle,
        {"from": deployer},
    )
    # DO NOT FORGET: Push initial constant value to cpi median oracle.
    # Median oracles will not return valid data on `getData()` and rebase
    # calls will fail if there are no valid reports within valid time range.
    digg.constantOracle.updateAndPush()
    # NB: Guarantee the configured report delay has passed. Otherwise,
    # the median oracle will attempt to use the last report.
    chain.sleep(digg_config_test.cpiOracleParams.reportDelaySec)

    # Setup frag policy & frag (required for ALL deploys).
    digg.uFragmentsPolicy.setCpiOracle(
        digg.cpiMedianOracle,
        {"from": deployer},
    )
    digg.uFragmentsPolicy.setMarketOracle(
        digg.marketMedianOracle,
        {"from": deployer},
    )
    digg.uFragmentsPolicy.setOrchestrator(
        digg.orchestrator,
        {"from": deployer},
    )
    digg.uFragmentsPolicy.setOrchestrator(
        digg.orchestrator,
        {"from": deployer},
    )
    digg.uFragments.setMonetaryPolicy(
        digg.uFragmentsPolicy,
        {"from": deployer},
    )

    return digg
