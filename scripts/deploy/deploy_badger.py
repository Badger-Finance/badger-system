#!/usr/bin/python3

from brownie import *
from config.badger_config import badger_config, badger_total_supply
from dotmap import DotMap
from helpers.constants import APPROVED_STAKER_ROLE
from helpers.registry import registry
from helpers.time_utils import daysToSeconds
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, print_to_file
from tests.conftest import create_uniswap_pair, distribute_from_whales

console = Console()


def test_deploy():
    deployer = accounts[0]

    # Ganache Accounts
    accounts.at("0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1", force=True)
    accounts.at("0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0", force=True)
    accounts.at("0x22d491Bde2303f2f43325b2108D26f1eAbA1e32b", force=True)
    accounts.at("0xE11BA2b4D45Eaed5996Cd0823791E0C93114882d", force=True)
    accounts.at("0xd03ea8624C8C5987235048901fB614fDcA89b117", force=True)
    accounts.at("0x95cED938F7991cd0dFcb48F0a06a40FA1aF46EBC", force=True)
    accounts.at("0x3E5e9111Ae8eB78Fe1CC3bb8915d5D461F3Ef9A9", force=True)
    accounts.at("0x28a8746e75304c0780E011BEd21C72cD78cd535E", force=True)
    accounts.at("0xACa94ef8bD5ffEE41947b4585a84BdA5a3d3DA6E", force=True)
    accounts.at("0x1dF62f291b2E969fB0849d99D9Ce41e2F137006e", force=True)

    # Unlocked Accounts
    accounts.at(
        web3.toChecksumAddress("0x193991827e291599a262e7fa7d212ff1ae31d110"), force=True
    )
    accounts.at(
        web3.toChecksumAddress("0x97ca371d59bbfefdb391aa6dcbdf4455fec361f2"), force=True
    )
    accounts.at(
        web3.toChecksumAddress("0x3d24d77bec08549d7ea86c4e9937204c11e153f1"), force=True
    )
    accounts.at(
        web3.toChecksumAddress("0xcD9e6Df80169b6a2CFfDaE613fAbC3F7C3647B14"), force=True
    )
    accounts.at(
        web3.toChecksumAddress("0xaf379f0228ad0d46bb7b4f38f9dc9bcc1ad0360c"), force=True
    )
    accounts.at(
        web3.toChecksumAddress("0xc25099792e9349c7dd09759744ea681c7de2cb66"), force=True
    )
    accounts.at(
        web3.toChecksumAddress("0xb1f2cdec61db658f091671f5f199635aef202cac"), force=True
    )
    accounts.at(
        web3.toChecksumAddress("0x2bf792ffe8803585f74e06907900c2dc2c29adcb"), force=True
    )

    # Test Accounts
    accounts.at(
        web3.toChecksumAddress("0xe7bab002A39f9672a1bD0E949d3128eeBd883575"), force=True
    )
    accounts.at(
        web3.toChecksumAddress("0x482c741b0711624d1f462E56EE5D8f776d5970dC"), force=True
    )

    for account in accounts:
        console.log(account)

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
    badger.deploy_geyser(badger.getSett("native.badger"), "native.badger")
    badger.deploy_geyser(badger.getSett("native.renCrv"), "native.renCrv")
    badger.deploy_geyser(badger.getSett("native.sbtcCrv"), "native.sbtcCrv")
    badger.deploy_geyser(badger.getSett("native.tbtcCrv"), "native.tbtcCrv")
    badger.deploy_geyser(badger.getSett("native.uniBadgerWbtc"), "native.uniBadgerWbtc")
    badger.deploy_geyser(badger.getSett("harvest.renCrv"), "harvest.renCrv")

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
        badger.getGeyser("native.badger"), {"from": deployer}
    )

    badger.rewardsEscrow.approveRecipient(
        badger.getGeyser("native.uniBadgerWbtc"), {"from": deployer}
    )

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
        Badger — 90,000 $BADGER / 2
            - 45000 in Sett StakingRewards
            - 45000 in Geyser
        Badger <>wBTC Uniswap LP — 130,000 $BADGER / 2
            - 65000 in Sett StakingRewards
            - 65000 in Geyser
        Super Sett
        Pickle renbtcCRV — 76,750 $BADGER
        Harvest renbtc CRV — 76,750 $BADGER
    """

    badger.signal_token_lock(
        "native.badger", badger_config.geyserParams.unlockSchedules.badger[0]
    )

    badger.signal_token_lock(
        "native.uniBadgerWbtc",
        badger_config.geyserParams.unlockSchedules.uniBadgerWbtc[0],
    )

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
