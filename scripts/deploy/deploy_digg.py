#!/usr/bin/python3
from helpers.utils import val
from scripts.systems.constants import SettType
from brownie import *
from rich.console import Console
import decouple

from scripts.systems.badger_system import BadgerSystem, print_to_file
from config.badger_config import digg_config, dao_config
from scripts.systems.digg_system import DiggSystem, connect_digg
from scripts.systems.digg_minimal import deploy_digg_minimal
from helpers.token_utils import distribute_from_whale
from helpers.registry import whale_registry
from config.badger_config import sett_config, digg_config_test
from helpers.constants import PAUSER_ROLE, UNPAUSER_ROLE
from helpers.time_utils import days

console = Console()


def test_deploy(test=False, deploy=True):
    # These should already be deployed
    deployer = accounts.at(decouple.config("TEST_ACCOUNT"), force=True)
    # deployer = accounts.at(dao_config.initialOwner, force=True)
    devProxyAdmin = "0x20dce41acca85e8222d6861aa6d23b6c941777bf"
    daoProxyAdmin = "0x11a9d034b1bbfbbdcac9cb3b86ca7d5df05140f2"
    console.log(
        "Initialize Digg System",
        {
            "deployer": deployer,
            "devProxyAdmin": devProxyAdmin,
            "daoProxyAdmin": daoProxyAdmin,
        },
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
        digg.diggTeamVesting, digg_config.founderRewardsAmount, {"from": deployer},
    )

    # == DAO Timelock ==
    digg.token.transfer(
        digg.daoDiggTimelock,
        digg_config.tokenLockParams.diggLockAmount,
        {"from": deployer},
    )


def deploy_sett_by_key(
    badger,
    key,
    strategyName,
    settType,
    params,
    deployer,
    strategist=None,
    governance=None,
    keeper=None,
    guardian=None,
):
    controller = badger.add_controller(key)
    vault = badger.deploy_sett(
        key,
        params.want,
        controller,
        governance=governance,
        strategist=strategist,
        keeper=keeper,
        guardian=guardian,
        sett_type=settType,
    )

    strategy = badger.deploy_strategy(
        key,
        strategyName,
        controller,
        params,
        governance=governance,
        strategist=strategist,
        keeper=keeper,
        guardian=guardian,
    )

    badger.wire_up_sett(vault, strategy, controller)

    assert vault.paused()
    vault.unpause({"from": governance})
    assert vault.paused() == False

def deploy_uni_digg_wbtc_lp_sett(badger, digg):
    """
    If test mode, add initial liquidity and distribute to test user
    """
    assert False

def deploy_sushi_digg_wbtc_lp_sett(badger, digg):
    """
    If test mode, add initial liquidity and distribute to test user
    """
    assert False

def deploy_digg_native_sett(badger, digg):
    deployer = badger.deployer
    key = "native.digg"
    params = sett_config.native.badger.params
    params.want = digg.token

    rewards = badger.deploy_digg_rewards_faucet("native.digg", digg.token)
    params.geyser = rewards

    deploy_sett_by_key(
        badger,
        key,
        "StrategyDiggRewards",
        SettType.DIGG,
        params,
        deployer=deployer,
        governance=badger.devMultisig,
        strategist=badger.deployer,
        keeper=badger.keeper,
        guardian=badger.guardian,
    )

    # Configure Rewards Faucet with initial distribution schedule
    console.print("[cyan]Configure native DIGG Sett Rewards Faucet...[/cyan]")
    strategy = badger.getStrategy(key)
    amount = digg_config_test.geyserParams.unlockSchedules.digg[0].amount

    print('digg.token.balanceOf(deployer)', digg.token.balanceOf(deployer), amount)
    assert digg.token.balanceOf(deployer) >= amount

    digg.token.transfer(rewards, amount, {"from": deployer})
    rewards.notifyRewardAmount(
        chain.time(), days(7), digg.token.fragmentsToShares(amount), {"from": deployer}
    )

    rewards.grantRole(PAUSER_ROLE, badger.keeper, {"from": deployer})
    rewards.grantRole(UNPAUSER_ROLE, badger.guardian, {"from": deployer})

    # Make strategy the recipient of the DIGG faucet
    rewards.initializeRecipient(strategy, {"from": deployer})

    if strategy.paused():
        strategy.unpause({"from": badger.devMultisig})


def deploy_digg_with_existing_badger(badger, test=False, outputToFile=True, testUser=None):

    deployer = badger.deployer

    # Deploy DIGG Core
    console.print("[green]== Deploy DIGG Core ==[/green]")
    digg = deploy_digg_minimal(
        deployer, badger.devProxyAdmin.address, badger.daoProxyAdmin.address, owner=deployer
    )

    # Deploy new logic contracts for DIGG Setts + Strategies
    console.print("[green]== Deploy Required Sett Logic ==[/green]")
    badger.deploy_logic("DiggRewardsFaucet", DiggRewardsFaucet)
    badger.deploy_logic("DiggSett", DiggSett)
    badger.deploy_sett_strategy_logic_for("StrategyDiggRewards")
    badger.deploy_sett_strategy_logic_for("StrategySushiDiggWbtcLpOptimizer")
    badger.deploy_sett_strategy_logic_for("StrategyDiggLpMetaFarm")

    console.print("[green]== Deploy & Configure Dynamic Oracle ==[/green]")
    # Deploy simple oracle
    digg.deploy_dynamic_oracle()

    digg.deploy_airdrop_distributor(digg_config.airdropRoot, badger.rewardsEscrow, digg_config.reclaimAllowedTimestamp)

    # Distribute required shares to airdrop


    # Setup simple oracle as provider
    digg.marketMedianOracle.addProvider(
        digg.dynamicOracle, {"from": deployer},
    )

    # Add DIGG to badger object
    badger.add_existing_digg(digg)

    console.print("[green]== Deploy DIGG Native Sett ==[/green]")
    deploy_digg_native_sett(badger, digg)

    # Verify all deployment parameters
    # Verify all initializers cannot be set twice
    # Verify all upgradability

    # Unit & integration tests vs live deployment before creation

    # Test Mode: Create LP Tokens & Distribute assets to test user
    if test:
        console.print("[green]== Test Mode Activities ==[/green]")
        remainingFree = badger.digg.token.balanceOf(deployer)
        console.print("Transfer remaining {} DIGG from deployer to test user {}".format(val(remainingFree), testUser.address))
        badger.digg.token.transfer(testUser, remainingFree, {'from': deployer})

        assert badger.digg.token.balanceOf(testUser) >= remainingFree

    console.print("[cyan]== Digg Supply ==[/cyan]")
    console.print({"totalShares": badger.digg.token.totalShares(), "totalSupply": badger.digg.token.totalSupply()})

    console.log("Test: Digg System Deployed")
    if outputToFile:
        fileName = "deploy-test-digg.json"
        console.log("Printing digg contract addresses to ", fileName)
        print_to_file(badger, fileName)
    if not test:
        post_deploy_config(digg)
    console.log("Test: Digg System Setup Complete")
    return digg


def digg_deploy_flow(test=False, outputToFile=True):
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
    return digg_deploy_flow(test=True, outputToFile=True)
