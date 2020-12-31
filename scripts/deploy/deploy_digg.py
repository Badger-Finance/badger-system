#!/usr/bin/python3
from brownie import accounts
from rich.console import Console

from config.badger_config import digg_config, dao_config
from scripts.systems.digg_system import DiggSystem, print_to_file, connect_digg
from scripts.systems.digg_minimal import deploy_digg_minimal
from helpers.token_utils import distribute_from_whale
from helpers.registry import whale_registry

console = Console()


def test_deploy(test=False, deploy=True):
    # These should already be deployed
    deployer = accounts.at(dao_config.initialOwner, force=True)
    devProxyAdmin = "0x20dce41acca85e8222d6861aa6d23b6c941777bf"
    daoProxyAdmin = "0x11a9d034b1bbfbbdcac9cb3b86ca7d5df05140f2"
    console.log(
        "Initialize Digg System",
        {"deployer": deployer, "devProxyAdmin": devProxyAdmin, "daoProxyAdmin": daoProxyAdmin},
    )

    if deploy:
        digg = deploy_digg_minimal(deployer, devProxyAdmin, daoProxyAdmin)
        digg.deploy_dao_digg_timelock()
        digg.deploy_digg_team_vesting()

        if test:
            # need some sweet liquidity for testing
            distribute_from_whale(whale_registry.wbtc, digg.owner)
        # deploy trading pairs (these deploys are always idempotent)
        digg.deploy_uniswap_pairs(test=test)  # adds liqudity in test mode
    else:
        digg = connect_digg(digg_config.prod_json)

    return digg


def post_deploy_config(digg: DiggSystem):
    """
    Set initial conditions on immediate post-deploy Digg

    Transfer tokens to their initial locations
    """
    deployer = digg.owner

    # == Team Vesting ==
    digg.token.transfer(
        digg.diggTeamVesting,
        digg_config.founderRewardsAmount,
        {"from": deployer},
    )

    # == DAO Timelock ==
    digg.token.transfer(
        digg.daoDiggTimelock,
        digg_config.tokenLockParams.diggLockAmount,
        {"from": deployer},
    )


def deploy_flow(test=False, outputToFile=True):
    digg = test_deploy(test=test)
    console.log("Test: Digg System Deployed")
    if outputToFile:
        fileName = "deploy-final-digg.json"
        console.log("Printing digg contract addresses to ", fileName)
        print_to_file(digg, fileName)
    if not test:
        post_deploy_config(digg)
    console.log("Test: Digg System Setup Complete")
    return digg


def main():
    return deploy_flow(test=True, outputToFile=False)
