from tests.helpers import create_uniswap_pair, distribute_from_whales
from scripts.systems.badger_system import deploy_badger
from scripts.systems.uniswap_system import UniswapSystem, connect_uniswap
from _pytest.config import get_config
from scripts.systems.badger_minimal import deploy_badger_minimal
import pytest
from brownie import *
from helpers.gnosis_safe import exec_direct
from scripts.deploy.deploy_badger import main
from helpers.registry import whale_registry
from helpers.constants import *
from config.badger_config import sett_config, badger_config
from helpers.registry import registry
from scripts.deploy.deploy_badger_with_actions import deploy_with_actions


@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    # perform a chain rewind after completing each test, to ensure proper isolation
    # https://eth-brownie.readthedocs.io/en/v1.10.3/tests-pytest-intro.html#isolation-fixtures
    pass


# @pytest.fixture()
def badger_single_sett(settId):
    if settId == "native.badger":
        return sett_native_badger()
    if settId == "native.renCrv":
        return sett_curve_gauge_renbtc()
    if settId == "native.sbtcCrv":
        return sett_curve_gauge_sbtc()
    if settId == "native.tbtcCrv":
        return sett_curve_gauge_tbtc()
    if settId == "native.uniBadgerWbtc":
        return sett_badger_lp_rewards()
    if settId == "pickle.renCrv":
        return sett_pickle_meta_farm()
    if settId == "harvest.renCrv":
        return sett_harvest_meta_farm()


def sett_native_badger():
    deployer = accounts[0]
    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    badger.deploy_logic("StrategyBadgerRewards", StrategyBadgerRewards)
    badger.deploy_logic("BadgerGeyser", BadgerGeyser)
    controller = badger.add_controller("native.badger")
    vault = badger.deploy_sett("native.badger", badger.token, controller)
    rewards = badger.deploy_sett_staking_rewards(
        "native.badger", badger.token, badger.token
    )

    params = sett_config.native.badger.params
    params.want = badger.token
    params.geyser = rewards

    strategy = badger.deploy_strategy(
        "native.badger", "StrategyBadgerRewards", controller, params
    )

    # want = badger.getStrategyWant('native.badger')

    badger.wire_up_sett(vault, strategy, controller)
    badger.distribute_staking_rewards(
        "native.badger", badger_config.geyserParams.unlockSchedules.badger[0].amount
    )

    # Approve Setts on specific
    rewards.grantRole(APPROVED_STAKER_ROLE, strategy, {"from": deployer})

    badger.deploy_geyser(badger.getSett("native.badger"), "native.badger")

    return badger


def sett_pickle_meta_farm():
    deployer = accounts[0]

    params = sett_config.pickle.renCrv.params
    want = sett_config.pickle.renCrv.params.want

    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    badger.deploy_logic("StrategyPickleMetaFarm", StrategyPickleMetaFarm)
    badger.deploy_logic("BadgerGeyser", BadgerGeyser)
    controller = badger.add_controller("pickle.renCrv")
    vault = badger.deploy_sett("pickle.renCrv", want, controller)

    strategy = badger.deploy_strategy(
        "pickle.renCrv", "StrategyPickleMetaFarm", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    return badger


def sett_harvest_meta_farm():
    deployer = accounts[0]

    params = sett_config.harvest.renCrv.params
    want = sett_config.harvest.renCrv.params.want

    badger = deploy_badger_minimal(deployer)
    params.badgerTree = badger.badgerTree
    distribute_from_whales(badger, deployer)

    badger.deploy_logic("StrategyHarvestMetaFarm", StrategyHarvestMetaFarm)
    badger.deploy_logic("BadgerGeyser", BadgerGeyser)
    controller = badger.add_controller("harvest.renCrv")
    vault = badger.deploy_sett("harvest.renCrv", want, controller)

    strategy = badger.deploy_strategy(
        "harvest.renCrv", "StrategyHarvestMetaFarm", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    badger.deploy_geyser(badger.getSett("harvest.renCrv"), "harvest.renCrv")

    return badger


def sett_curve_gauge_renbtc():
    deployer = accounts[0]

    params = sett_config.native.renCrv.params
    want = sett_config.native.renCrv.params.want

    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    badger.deploy_logic("StrategyCurveGaugeRenBtcCrv", StrategyCurveGaugeRenBtcCrv)
    badger.deploy_logic("BadgerGeyser", BadgerGeyser)
    controller = badger.add_controller("native.renCrv")
    vault = badger.deploy_sett("native.renCrv", want, controller)

    strategy = badger.deploy_strategy(
        "native.renCrv", "StrategyCurveGaugeRenBtcCrv", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    badger.deploy_geyser(badger.getSett("native.renCrv"), "native.renCrv")

    return badger


def sett_curve_gauge_sbtc():
    deployer = accounts[0]

    params = sett_config.native.sbtcCrv.params
    want = sett_config.native.sbtcCrv.params.want

    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    badger.deploy_logic("StrategyCurveGaugeSbtcCrv", StrategyCurveGaugeSbtcCrv)
    badger.deploy_logic("BadgerGeyser", BadgerGeyser)
    controller = badger.add_controller("native.sbtcCrv")
    vault = badger.deploy_sett("native.sbtcCrv", want, controller)

    strategy = badger.deploy_strategy(
        "native.sbtcCrv", "StrategyCurveGaugeSbtcCrv", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    badger.deploy_geyser(badger.getSett("native.sbtcCrv"), "native.sbtcCrv")

    return badger


def sett_curve_gauge_tbtc():
    deployer = accounts[0]

    params = sett_config.native.tbtcCrv.params
    want = sett_config.native.tbtcCrv.params.want

    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    badger.deploy_logic("StrategyCurveGaugeTbtcCrv", StrategyCurveGaugeTbtcCrv)
    badger.deploy_logic("BadgerGeyser", BadgerGeyser)
    controller = badger.add_controller("native.tbtcCrv")
    vault = badger.deploy_sett("native.tbtcCrv", want, controller)

    strategy = badger.deploy_strategy(
        "native.tbtcCrv", "StrategyCurveGaugeTbtcCrv", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    badger.deploy_geyser(badger.getSett("native.tbtcCrv"), "native.tbtcCrv")

    return badger


def sett_badger_lp_rewards():
    deployer = accounts[0]

    # TODO: Deploy UNI pool and add liquidity in order to get want

    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    pair = create_uniswap_pair(badger.token.address, registry.tokens.wbtc, deployer)

    badger.pair = pair
    want = pair

    rewards = badger.deploy_sett_staking_rewards(
        "native.uniBadgerWbtc", pair.address, badger.token
    )

    assert rewards.rewardsToken() == badger.token
    assert rewards.stakingToken() == pair

    badger.deploy_logic("StrategyBadgerLpMetaFarm", StrategyBadgerLpMetaFarm)
    badger.deploy_logic("BadgerGeyser", BadgerGeyser)
    controller = badger.add_controller("native.uniBadgerWbtc")
    vault = badger.deploy_sett("native.uniBadgerWbtc", want, controller)

    params = sett_config.native.uniBadgerWbtc.params
    params.want = badger.pair
    params.geyser = rewards

    strategy = badger.deploy_strategy(
        "native.uniBadgerWbtc", "StrategyBadgerLpMetaFarm", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    wbtc = interface.IERC20(registry.tokens.wbtc)

    # Grant deployer LP tokens
    badger.uniswap.addMaxLiquidity(badger.token, wbtc, deployer)

    badger.distribute_staking_rewards(
        "native.uniBadgerWbtc", badger_config.geyserParams.unlockSchedules.uniBadgerWbtc[0].amount
    )

    rewards.grantRole(APPROVED_STAKER_ROLE, strategy, {"from": deployer})

    badger.deploy_geyser(badger.getSett("native.uniBadgerWbtc"), "native.uniBadgerWbtc")

    return badger


@pytest.fixture()
def badger(accounts):
    badger_system = main()

    # Distribute Test Assets

    return badger_system


@pytest.fixture()
def badger_with_actions(accounts):
    return deploy_with_actions()

