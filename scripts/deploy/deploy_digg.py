#!/usr/bin/python3
from scripts.systems.aragon_system import AragonSystem
from helpers.proxy_utils import deploy_proxy
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
import time
from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.sushiswap_system import SushiswapSystem
from helpers.utils import val
from scripts.systems.constants import SettType
from brownie import *
from rich.console import Console
import decouple

from scripts.systems.badger_system import BadgerSystem, connect_badger, print_to_file
from config.badger_config import digg_config, dao_config
from scripts.systems.digg_system import DiggSystem, connect_digg
from scripts.systems.digg_minimal import deploy_digg_minimal
from helpers.token_utils import distribute_from_whale
from helpers.registry import whale_registry, registry
from config.badger_config import sett_config, digg_config_test
from helpers.constants import (
    DEFAULT_ADMIN_ROLE,
    PAUSER_ROLE,
    TOKEN_LOCKER_ROLE,
    UNPAUSER_ROLE,
)
from helpers.time_utils import days
from helpers.registry import token_registry

console = Console()

sleep_between_tx = 1


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
    controller = badger.getController("native")
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
    time.sleep(sleep_between_tx)

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
    time.sleep(sleep_between_tx)

    # badger.wire_up_sett(vault, strategy, controller)

    assert vault.paused()
    # vault.unpause({"from": governance})
    # assert vault.paused() == False


def deploy_uni_digg_wbtc_lp_sett(badger, digg):
    """
    If test mode, add initial liquidity and distribute to test user
    """
    deployer = badger.deployer
    key = "native.uniDiggWbtc"
    params = sett_config.uni.uniDiggWbtc.params
    uniswap = UniswapSystem()
    params.want = uniswap.getPair(digg.token, registry.tokens.wbtc)
    params.token = digg.token

    rewards = badger.deploy_digg_rewards_faucet(key, digg.token)
    params.geyser = rewards

    time.sleep(sleep_between_tx)

    deploy_sett_by_key(
        badger,
        key,
        "StrategyDiggLpMetaFarm",
        SettType.DEFAULT,
        params,
        deployer=deployer,
        governance=badger.devMultisig,
        strategist=badger.deployer,
        keeper=badger.keeper,
        guardian=badger.guardian,
    )
    # assert False

    strategy = badger.getStrategy(key)

    rewards.grantRole(PAUSER_ROLE, badger.keeper, {"from": deployer})
    rewards.grantRole(UNPAUSER_ROLE, badger.devMultisig, {"from": deployer})

    # Make strategy the recipient of the DIGG faucet
    rewards.initializeRecipient(strategy, {"from": deployer})


def deploy_sushi_digg_wbtc_lp_sett(badger, digg):
    """
    If test mode, add initial liquidity and distribute to test user
    """
    deployer = badger.deployer
    key = "native.sushiDiggWbtc"
    params = sett_config.sushi.sushiDiggWBtc.params

    sushiswap = SushiswapSystem()

    params.want = sushiswap.getPair(digg.token, registry.tokens.wbtc)
    params.token = digg.token
    params.badgerTree = badger.badgerTree

    # params.pid = sushiswap.add_chef_rewards(params.want)
    # print("pid", params.pid)
    params.pid = 103

    # Deploy Rewards
    rewards = badger.deploy_digg_rewards_faucet(key, digg.token)
    params.geyser = rewards

    time.sleep(sleep_between_tx)

    deploy_sett_by_key(
        badger,
        key,
        "StrategySushiDiggWbtcLpOptimizer",
        SettType.DEFAULT,
        params,
        deployer=deployer,
        governance=badger.devMultisig,
        strategist=badger.deployer,
        keeper=badger.keeper,
        guardian=badger.guardian,
    )
    # assert False

    strategy = badger.getStrategy(key)

    rewards.grantRole(PAUSER_ROLE, badger.keeper, {"from": deployer})
    rewards.grantRole(UNPAUSER_ROLE, badger.devMultisig, {"from": deployer})

    # Make strategy the recipient of the DIGG faucet
    rewards.initializeRecipient(strategy, {"from": deployer})


def deploy_digg_native_sett(badger: BadgerSystem, digg):
    deployer = badger.deployer
    key = "native.digg"
    params = sett_config.native.badger.params
    params.want = digg.token

    rewards = badger.deploy_digg_rewards_faucet(key, digg.token)
    time.sleep(sleep_between_tx)

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

    strategy = badger.getStrategy(key)

    rewards.grantRole(PAUSER_ROLE, badger.keeper, {"from": deployer})
    rewards.grantRole(UNPAUSER_ROLE, badger.devMultisig, {"from": deployer})

    # Make strategy the recipient of the DIGG faucet
    rewards.initializeRecipient(strategy, {"from": deployer})

    # if strategy.paused():
    #     strategy.unpause({"from": badger.devMultisig})


def init_prod_digg(badger: BadgerSystem, user):
    deployer = badger.deployer

    digg = badger.digg

    multi = GnosisSafe(badger.devMultisig)

    digg_liquidity_amount = 1000000000
    wbtc_liquidity_amount = 100000000

    print("TOKEN_LOCKER_ROLE", TOKEN_LOCKER_ROLE)
    locker_role = "0x4bf6f2cdcc8ad6c087a7a4fbecf46150b3686b71387234cac2b3e2e6dc70e345"

    # TODO: Have this as proxy in real deploy
    seederLogic = DiggSeeder.deploy({"from": deployer})

    seeder = deploy_proxy(
        "DiggSeeder",
        DiggSeeder.abi,
        seederLogic.address,
        badger.devProxyAdmin.address,
        seederLogic.initialize.encode_input(digg.diggDistributor),
        deployer,
    )

    # # Take initial liquidity from DAO
    # aragon = AragonSystem()
    # voting = aragon.getVotingAt("0xdc344bfb12522bf3fa58ef0d6b9a41256fc79a1b")

    # PROD: Configure DIGG
    digg.uFragmentsPolicy.setCpiOracle(
        digg.cpiMedianOracle, {"from": deployer},
    )
    digg.uFragmentsPolicy.setMarketOracle(
        digg.marketMedianOracle, {"from": deployer},
    )
    digg.uFragmentsPolicy.setOrchestrator(
        digg.orchestrator, {"from": deployer},
    )
    digg.uFragments.setMonetaryPolicy(
        digg.uFragmentsPolicy, {"from": deployer},
    )

    # ===== Upgrade DAOTimelock to allow voting =====
    # print(badger.logic.SimpleTimelockWithVoting.address)
    # timelockWithVotingLogic = SimpleTimelockWithVoting.at(badger.logic.SimpleTimelockWithVoting.address)
    # timelock = interface.ISimpleTimelockWithVoting(badger.daoBadgerTimelock.address)

    # multi.execute(
    #     MultisigTxMetadata(description="Upgrade DAO Badger Timelock to Allow voting",),
    #     {
    #         "to": badger.devProxyAdmin.address,
    #         "data": badger.devProxyAdmin.upgrade.encode_input(
    #             badger.daoBadgerTimelock, timelockWithVotingLogic
    #         ),
    #     },
    # )

    # # ===== Vote to move initial liquidity funds to multisig  =====
    # tx = multi.execute(
    #     MultisigTxMetadata(description="Vote on DAO Timelock from multisig",),
    #     {
    #         "to": timelock.address,
    #         "data": timelock.vote.encode_input(0, True, True)
    #     },
    # )

    # # Approve DAO voting as recipient
    # multi.execute(
    #     MultisigTxMetadata(description="Approve DAO voting as recipient",),
    #     {
    #         "to": badger.rewardsEscrow.address,
    #         "data": badger.rewardsEscrow.approveRecipient.encode_input(voting),
    #     },
    # )

    # # Vote on DAO voting as rewardsEscrow

    # before = badger.token.balanceOf(badger.rewardsEscrow)

    # tx = multi.execute(
    #     MultisigTxMetadata(description="Vote on Rewards Escrow from multisig",),
    #     {
    #         "to": badger.rewardsEscrow.address,
    #         "data": badger.rewardsEscrow.call.encode_input(
    #             voting, 0, voting.vote.encode_input(0, True, True)
    #         ),
    #     },
    # )

    # after = badger.token.balanceOf(badger.rewardsEscrow)

    # print(tx.call_trace())

    # assert after == before

    # crvRen = interface.IERC20(registry.curve.pools.renCrv.token)
    wbtc = interface.IERC20(registry.tokens.wbtc)
    # assert crvRen.balanceOf(badger.devMultisig) >= wbtc_liquidity_amount * 10 ** 10 * 2

    # crvPool = interface.ICurveZap(registry.curve.pools.renCrv.swap)

    # # crvPool.Remove_liquidity_one_coin(
    # #     wbtc_liquidity_amount * 10 ** 10, 1, wbtc_liquidity_amount
    # # )

    # # ===== Convert crvRen to wBTC on multisig =====
    # tx = multi.execute(
    #     MultisigTxMetadata(description="Withdraw crvRen for 100% WBTC",),
    #     {
    #         "to": crvPool.address,
    #         "data": crvPool.remove_liquidity_one_coin.encode_input(
    #             wbtc_liquidity_amount * 10 ** 10 * 2, 1, wbtc_liquidity_amount * 2
    #         ),
    #     },
    # )

    # assert wbtc.balanceOf(badger.devMultisig) >= wbtc_liquidity_amount * 2

    # ===== Move initial liquidity funds to Seeder =====
    multi.execute(
        MultisigTxMetadata(
            description="Transfer initial liquidity WBTC to the Seeder",
        ),
        {"to": wbtc.address, "data": wbtc.transfer.encode_input(seeder, 200000000),},
    )

    # ===== Move DIGG to Seeder =====
    digg.token.transfer(seeder, digg.token.totalSupply(), {"from": deployer})

    # ===== Move Required Badger to Seeder from RewardsEscrow =====
    multi.execute(
        MultisigTxMetadata(
            description="Move Required Badger to Seeder from RewardsEscrow",
        ),
        {
            "to": badger.rewardsEscrow.address,
            "data": badger.rewardsEscrow.transfer.encode_input(
                badger.token, seeder, Wei("30000 ether")
            ),
        },
    )

    # ===== Add DIGG token to all geyser distribution lists =====
    # (Also, add Seeder as approved schedule creator)
    geyser_keys = [
        "native.badger",
        "native.renCrv",
        "native.sbtcCrv",
        "native.tbtcCrv",
        "native.uniBadgerWbtc",
        "harvest.renCrv",
        "native.sushiWbtcEth",
        "native.sushiBadgerWbtc",
        "native.uniDiggWbtc",
        "native.sushiDiggWbtc",
    ]

    for key in geyser_keys:
        geyser = badger.getGeyser(key)
        print(key, geyser)
        id = multi.addTx(
            MultisigTxMetadata(
                description="Add DIGG token to distribution tokens on {} geyser".format(
                    key
                ),
            ),
            {
                "to": geyser.address,
                "data": geyser.addDistributionToken.encode_input(digg.token),
            },
        )

        tx = multi.executeTx(id)

        assert geyser.hasRole(DEFAULT_ADMIN_ROLE, badger.devMultisig)

        multi.execute(
            MultisigTxMetadata(
                description="Allow Seeder to set unlock schedules on {} geyser".format(
                    key
                ),
            ),
            {
                "to": geyser.address,
                "data": geyser.grantRole.encode_input(locker_role, seeder),
            },
        )

        assert geyser.hasRole(locker_role, seeder)

    # Seeder needs to have admin role to config Faucets. Remove role as part of seed.
    rewards_keys = [
        "native.digg",
        "native.uniDiggWbtc",
        "native.sushiDiggWbtc",
    ]

    for key in rewards_keys:
        rewards = badger.getSettRewards(key)
        rewards.grantRole(DEFAULT_ADMIN_ROLE, seeder, {"from": deployer})
        rewards.grantRole(DEFAULT_ADMIN_ROLE, badger.devMultisig, {"from": deployer})
        rewards.renounceRole(DEFAULT_ADMIN_ROLE, deployer, {"from": deployer})

    # print(digg.token.balanceOf(deployer))
    # assert digg.token.balanceOf(deployer) == digg.token.totalSupply()
    # digg.token.transfer(seeder, digg.token.totalSupply(), {"from": deployer})
    # wbtc = interface.IERC20(token_registry.wbtc)
    # wbtc.transfer(seeder, 200000000, {"from": user})

    # ===== Seed Prep =====

    print("wbtc.balanceOf(seeder)", wbtc.balanceOf(seeder))
    assert digg.token.balanceOf(seeder) >= digg.token.totalSupply()
    assert wbtc.balanceOf(seeder) >= 200000000

    print(digg.diggDistributor.address)
    print("digg.diggDistributor", digg.diggDistributor.isOpen())
    digg.diggDistributor.transferOwnership(seeder, {"from": deployer})

    print("prePreSeed", digg.token.balanceOf(seeder))

    seeder.preSeed({"from": deployer})

    print("postPreSeed", digg.token.balanceOf(seeder))

    seeder.seed({"from": deployer})

    # seeder.transferOwnership(badger.devMultisig, {'from': deployer})

    # tx = multi.execute(
    #     MultisigTxMetadata(description="Withdraw crvRen for 100% WBTC",),
    #     {
    #         "to": seeder.address,
    #         "data": seeder.preSeed.encode_input(),
    #     },
    # )

    # seeder.initialize({"from": deployer})

    # Unpause all Setts
    setts_to_unpause = [
        "native.digg",
        "native.uniDiggWbtc",
        "native.sushiDiggWbtc",
    ]

    for key in setts_to_unpause:
        sett = badger.getSett(key)

        id = multi.addTx(
            MultisigTxMetadata(description="Unpause Sett {}".format(key),),
            {"to": sett.address, "data": sett.unpause.encode_input(),},
        )

        tx = multi.executeTx(id)
        assert sett.paused() == False


def deploy_digg_with_existing_badger(
    badger, test=False, outputToFile=True, testUser=None
):

    deployer = badger.deployer

    # Deploy DIGG Core
    console.print("[green]== Deploy DIGG Core ==[/green]")
    digg = deploy_digg_minimal(
        deployer,
        badger.devProxyAdmin.address,
        badger.daoProxyAdmin.address,
        owner=deployer,
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

    digg.deploy_airdrop_distributor(
        digg_config.airdropRoot,
        badger.rewardsEscrow,
        digg_config.reclaimAllowedTimestamp,
    )

    # Distribute required shares to airdrop

    # Setup simple oracle as provider
    digg.marketMedianOracle.addProvider(
        digg.dynamicOracle, {"from": deployer},
    )

    # Add DIGG to badger object
    badger.add_existing_digg(digg)

    console.print("[green]== Deploy DIGG Native Sett ==[/green]")
    deploy_digg_native_sett(badger, digg)

    # Configure Rewards Faucet with initial distribution schedule
    # console.print("[cyan]Configure native DIGG Sett Rewards Faucet...[/cyan]")
    # strategy = badger.getStrategy(key)
    # amount = digg_config_test.geyserParams.unlockSchedules.digg[0].amount

    # print('digg.token.balanceOf(deployer)', digg.token.balanceOf(deployer), amount)
    # assert digg.token.balanceOf(deployer) >= amount

    # digg.token.transfer(rewards, amount, {"from": deployer})
    # rewards.notifyRewardAmount(
    #     chain.time(), days(7), digg.token.fragmentsToShares(amount), {"from": deployer}
    # )

    # Initial DIGG Distribution

    # Liquidity Mining Pool -> Rewards Escrow
    # Team Pool -> Team Vesting
    #

    # Verify all deployment parameters
    # Verify all initializers cannot be set twice
    # Verify all upgradability

    # Unpause All Setts

    # Unit & integration tests vs live deployment before creation

    # Test Mode: Create LP Tokens & Distribute assets to test user
    if test:
        console.print("[green]== Test Mode Activities ==[/green]")
        remainingFree = badger.digg.token.balanceOf(deployer)
        console.print(
            "Transfer remaining {} DIGG from deployer to test user {}".format(
                val(remainingFree), testUser.address
            )
        )
        badger.digg.token.transfer(testUser, remainingFree, {"from": deployer})

        assert badger.digg.token.balanceOf(testUser) >= remainingFree

    console.print("[cyan]== Digg Supply ==[/cyan]")
    console.print(
        {
            "totalShares": badger.digg.token.totalShares(),
            "totalSupply": badger.digg.token.totalSupply(),
        }
    )

    console.log("Test: Digg System Deployed")
    if outputToFile:
        fileName = "deploy-final.json"
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
