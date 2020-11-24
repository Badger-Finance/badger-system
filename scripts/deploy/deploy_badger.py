#!/usr/bin/python3

import time
from helpers.time_utils import daysToSeconds
from helpers.constants import APPROVED_STAKER_ROLE
from tests.conftest import create_uniswap_pair, distribute_from_whales
from scripts.systems.badger_system import (
    BadgerSystem,
    print_to_file,
)
from brownie import *
from helpers.registry import registry
from dotmap import DotMap
from config.badger_config import badger_config, badger_total_supply


def test_deploy():
    deployer = accounts[0]

    print("Initialize Badger System")
    badger = BadgerSystem(badger_config, None, deployer)

    print("Test: Distribute assets to deployer")
    badger.token.transfer(
        deployer, badger_total_supply, {"from": badger_config.dao.initialOwner}
    )
    distribute_from_whales(badger, deployer)

    print("Test: Create Badger<>wBTC LP Pair")
    pair = create_uniswap_pair(badger.token.address, registry.tokens.wbtc, deployer)
    badger.pair = pair

    print("Test: Add Badger<>wBTC Liquidity")
    wbtc = interface.IERC20(registry.tokens.wbtc)
    badger.uniswap.addMaxLiquidity(badger.token, wbtc, deployer)

    print("Deploy core logic")
    badger.deploy_core_logic()

    print("Deploy Sett core logic")
    badger.deploy_sett_core_logic()
    badger.deploy_sett_strategy_logic()

    print("Deploy rewards & vesting infrastructure")
    badger.deploy_rewards_escrow()
    badger.deploy_badger_tree()
    badger.deploy_dao_badger_timelock()
    badger.deploy_team_vesting()
    badger.deploy_badger_hunt()

    print("Deploy Sett controllers")
    badger.add_controller("native")
    badger.add_controller("harvest")

    print("Deploy native Sett vaults")
    controller = badger.getController("native")
    badger.deploy_sett("native.badger", badger.token, controller)
    badger.deploy_sett("native.renCrv", registry.curve.pools.renCrv.token, controller)
    badger.deploy_sett("native.sbtcCrv", registry.curve.pools.sbtcCrv.token, controller)
    badger.deploy_sett("native.tbtcCrv", registry.curve.pools.tbtcCrv.token, controller)
    badger.deploy_sett("native.uniBadgerWbtc", badger.pair.address, controller)

    print("Deploy & configure native Sett strategies")
    # Deploy vault-specific staking rewards
    badger.deploy_sett_staking_rewards("native.badger", badger.token, badger.token)

    badger.deploy_sett_staking_rewards(
        "native.uniBadgerWbtc", pair.address, badger.token
    )

    badger.deploy_strategy_native_badger()
    badger.deploy_strategy_native_rencrv()
    badger.deploy_strategy_native_sbtccrv()
    badger.deploy_strategy_native_tbtccrv()
    badger.deploy_strategy_native_uniBadgerWbtc()

    print("Deploy harvest Sett vaults")
    controller = badger.getController("harvest")
    badger.deploy_sett(
        "harvest.renCrv",
        registry.curve.pools.renCrv.token,
        controller,
        namePrefixOverride=True,
        namePrefix="Badger SuperSett (Harvest)",
        symbolPrefix="bsuper",
    )

    print("Deploy & configure harvest Sett strategies")
    badger.deploy_strategy_harvest_rencrv()

    print("Deploy reward geysers")
    badger.deploy_geyser(badger.token, "native.badger")
    badger.deploy_geyser(badger.token, "native.renCrv")
    badger.deploy_geyser(badger.token, "native.sbtcCrv")
    badger.deploy_geyser(badger.token, "native.tbtcCrv")
    badger.deploy_geyser(badger.token, "native.uniBadgerWbtc")
    badger.deploy_geyser(badger.token, "harvest.renCrv")

    # Transfer ownership of all sett Rewards contracts to multisig
    # Transfer proxyAdmin to multisig

    return badger


def post_deploy_config(badger: BadgerSystem):
    deployer = badger.deployer

    """
    Set initial conditions on immediate post-deploy Badger

    Transfer tokens to thier initial locations
        - Rewards Escrow (50%, minus tokens initially distributed via Sett Special StakingRewards)
        - Badger Hurt (15%)
        - DAO Timelock (35%)
    """

    # Approve BadgerTree to recieve rewards tokens
    badger.rewardsEscrow.approveRecipient(badger.badgerTree, {"from": deployer})

    badger.rewardsEscrow.approveRecipient(
        badger.getGeyser("native.renCrv"), {"from": deployer}
    )

    badger.rewardsEscrow.approveRecipient(
        badger.getGeyser("native.sbtcCrv"), {"from": deployer}
    )

    badger.rewardsEscrow.approveRecipient(
        badger.getGeyser("native.tbtcCrv"), {"from": deployer}
    )

    badger.rewardsEscrow.approveRecipient(
        badger.getGeyser("harvest.renCrv"), {"from": deployer}
    )

    # Geyser Signals
    """
        These signals are used to calculate the rewards distributions distributed via BadgerTree. The tokens are actually held in the RewardsEscrow and sent to the BadgerTree as needed.

        The escrow will only send a few days worth of rewards initially at a time to the RewardsTree as another failsafe mechanism.

        renbtcCRV — 76750 $BADGER
        sbtcCRV — 76,750 $BADGER
        tbtcCRV — 76,750 $BADGER
        Badger — 90,000 $BADGER
        Badger <>wBTC Uniswap LP — 130,000 $BADGER
        Super Sett
        Pickle renbtcCRV — 76,750 $BADGER
        Harvest renbtc CRV — 76,750 $BADGER
    """
    badger.signal_token_lock(
        "native.renCrv", badger_config.geyserParams.unlockSchedules.bRenCrv[0]
    )

    badger.signal_token_lock(
        "native.sbtcCrv", badger_config.geyserParams.unlockSchedules.bSbtcCrv[0]
    )

    badger.signal_token_lock(
        "native.tbtcCrv", badger_config.geyserParams.unlockSchedules.bTbtcCrv[0]
    )

    badger.signal_token_lock(
        "harvest.renCrv",
        badger_config.geyserParams.unlockSchedules.bSuperRenCrvHarvest[0],
    )

    # ===== Initial Token Distribution =====
    # == Native Badger ==
    rewards = badger.getSettRewards("native.badger")
    strategy = badger.getStrategy("native.badger")

    badger.distribute_staking_rewards(
        "native.badger",
        badger_config.geyserParams.unlockSchedules.uniBadgerWbtc[0].amount,
        notify=False,
    )
    rewards.grantRole(APPROVED_STAKER_ROLE, strategy, {"from": deployer})

    # == Uni LP ==
    rewards = badger.getSettRewards("native.uniBadgerWbtc")
    strategy = badger.getStrategy("native.uniBadgerWbtc")

    badger.distribute_staking_rewards(
        "native.uniBadgerWbtc",
        badger_config.geyserParams.unlockSchedules.uniBadgerWbtc[0].amount,
        notify=False,
    )
    rewards.grantRole(APPROVED_STAKER_ROLE, strategy, {"from": deployer})

    distributedToPools = (
        badger_config.geyserParams.unlockSchedules.badger[0].amount
        + badger_config.geyserParams.unlockSchedules.uniBadgerWbtc[0].amount
    )

    toEscrow = badger_config.rewardsEscrowBadgerAmount - distributedToPools

    # ===== Rewards Escrow =====
    badger.token.transfer(
        badger.rewardsEscrow, toEscrow, {"from": deployer},
    )

    # ===== Badger Hunt =====
    badger.token.transfer(
        badger.badgerHunt, badger_config.huntParams.badgerAmount, {"from": deployer},
    )

    # ===== DAO Timelock =====
    badger.token.transfer(
        badger.daoBadgerTimelock,
        badger_config.tokenLockParams.badgerLockAmount,
        {"from": deployer},
    )


def start_staking_rewards(badger: BadgerSystem):
    """
    StakingRewards contracts start immediately when the first tokens are locked
    """
    # == Badger ==
    deployer = badger.deployer
    rewards = badger.getSettRewards("native.badger")

    print(rewards)

    assert (
        badger.token.balanceOf(rewards)
        >= badger_config.geyserParams.unlockSchedules.badger[0].amount
    )
    assert rewards.stakingToken() == badger.token
    assert rewards.rewardsToken() == badger.token

    rewards.notifyRewardAmount(
        badger_config.geyserParams.unlockSchedules.badger[0].amount, {"from": deployer}
    )

    # == Uni LP ==
    rewards = badger.getSettRewards("native.uniBadgerWbtc")

    print(rewards)

    assert (
        badger.token.balanceOf(rewards)
        >= badger_config.geyserParams.unlockSchedules.uniBadgerWbtc[0].amount
    )
    assert rewards.stakingToken() == badger.pair
    assert rewards.rewardsToken() == badger.token

    rewards.notifyRewardAmount(
        badger_config.geyserParams.unlockSchedules.uniBadgerWbtc[0].amount,
        {"from": deployer},
    )


def main():
    badger = test_deploy()
    print("Test: Badger System Deployed")
    post_deploy_config(badger)
    start_staking_rewards(badger)
    print("Test: Badger System Setup Complete")
    print("Printing contract addresses to local.json")
    print_to_file(badger, "local.json")
    return badger
