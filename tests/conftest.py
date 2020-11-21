from _pytest.config import get_config
from scripts.systems.badger_minimal import deploy_badger_minimal
import pytest
from brownie import *
from helpers.gnosis_safe import exec_direct
from scripts.deploy.deploy_badger import main
from helpers.registry import whale_registry
from helpers.constants import *
from config.badger_config import sett_config, badger_config


@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    # perform a chain rewind after completing each test, to ensure proper isolation
    # https://eth-brownie.readthedocs.io/en/v1.10.3/tests-pytest-intro.html#isolation-fixtures
    pass


def distribute_test_assets(badger):
    distribute_rewards_escrow(
        badger, badger.token, badger.deployer, Wei("100000 ether")
    )
    distribute_from_whales(badger, badger.deployer)


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

    badger.add_logic("StrategyBadgerRewards", StrategyBadgerRewards)
    controller = badger.add_controller("native.badger")
    vault = badger.add_sett(
        "native.badger", badger.token, controller, "Badger Sett badger", "bBadger"
    )
    rewards = badger.deploy_sett_staking_rewards(
        "native.badger", badger.token, badger.token
    )

    params = sett_config.native.badger.params
    params.want = badger.token
    params.geyser = rewards

    strategy = badger.add_strategy(
        "native.badger", "StrategyBadgerRewards", controller, params
    )

    # want = badger.getStrategyWant('native.badger')

    badger.wire_up_sett(vault, strategy, controller)
    badger.distribute_staking_rewards(
        rewards, badger_config.geyserParams.unlockSchedules.badger[0].amount
    )

    # Approve Setts on specific
    rewards.grantRole(APPROVED_STAKER_ROLE, strategy, {"from": deployer})

    return badger


def sett_pickle_meta_farm():
    deployer = accounts[0]

    params = sett_config.pickle.renCrv.params
    want = sett_config.pickle.renCrv.params.want

    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    badger.add_logic("StrategyPickleMetaFarm", StrategyPickleMetaFarm)
    controller = badger.add_controller("pickle.renCrv")
    vault = badger.add_sett(
        "pickle.renCrv", want, controller, "Badger Sett badger", "bBadger"
    )

    strategy = badger.add_strategy(
        "pickle.renCrv", "StrategyPickleMetaFarm", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    return badger


def sett_harvest_meta_farm():
    deployer = accounts[0]

    params = sett_config.harvest.renCrv.params
    want = sett_config.harvest.renCrv.params.want

    badger = deploy_badger_minimal(deployer)
    params.rewardsEscrow = badger.rewardsEscrow
    distribute_from_whales(badger, deployer)

    badger.add_logic("StrategyHarvestMetaFarm", StrategyHarvestMetaFarm)
    controller = badger.add_controller("harvest.renCrv")
    vault = badger.add_sett(
        "harvest.renCrv", want, controller, "Badger Sett badger", "bBadger"
    )

    strategy = badger.add_strategy(
        "harvest.renCrv", "StrategyHarvestMetaFarm", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    return badger


def sett_curve_gauge_renbtc():
    deployer = accounts[0]

    params = sett_config.native.renCrv.params
    want = sett_config.native.renCrv.params.want

    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    badger.add_logic("StrategyCurveGaugeRenBtcCrv", StrategyCurveGaugeRenBtcCrv)
    controller = badger.add_controller("native.renCrv")
    vault = badger.add_sett(
        "native.renCrv", want, controller, "Badger Sett badger", "bBadger"
    )

    strategy = badger.add_strategy(
        "native.renCrv", "StrategyCurveGaugeRenBtcCrv", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    return badger


def sett_curve_gauge_sbtc():
    deployer = accounts[0]

    params = sett_config.native.sbtcCrv.params
    want = sett_config.native.sbtcCrv.params.want

    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    badger.add_logic("StrategyCurveGaugeSbtcCrv", StrategyCurveGaugeSbtcCrv)
    controller = badger.add_controller("native.sbtcCrv")
    vault = badger.add_sett(
        "native.sbtcCrv", want, controller, "Badger Sett badger", "bBadger"
    )

    strategy = badger.add_strategy(
        "native.sbtcCrv", "StrategyCurveGaugeSbtcCrv", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    return badger


def sett_curve_gauge_tbtc():
    deployer = accounts[0]

    params = sett_config.native.tbtcCrv.params
    want = sett_config.native.tbtcCrv.params.want

    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    badger.add_logic("StrategyCurveGaugeTbtcCrv", StrategyCurveGaugeTbtcCrv)
    controller = badger.add_controller("native.tbtcCrv")
    vault = badger.add_sett(
        "native.tbtcCrv", want, controller, "Badger Sett badger", "bBadger"
    )

    strategy = badger.add_strategy(
        "native.tbtcCrv", "StrategyCurveGaugeTbtcCrv", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    return badger


def sett_badger_lp_rewards():
    deployer = accounts[0]

    params = sett_config.native.uniBadgerWbtc.params

    # TODO: Deploy UNI pool and add liquidity in order to get want
    want = sett_config.native.uniBadgerWbtc.params.want

    badger = deploy_badger_minimal(deployer)
    distribute_from_whales(badger, deployer)

    badger.add_logic("StrategyBadgerLpMetaFarm", StrategyBadgerLpMetaFarm)
    controller = badger.add_controller("native.uniBadgerWbtc")
    vault = badger.add_sett(
        "native.uniBadgerWbtc", want, controller, "Badger Sett badger", "bBadger"
    )

    strategy = badger.add_strategy(
        "native.uniBadgerWbtc", "StrategyBadgerLpMetaFarm", controller, params
    )

    badger.wire_up_sett(vault, strategy, controller)

    return badger


@pytest.fixture()
def badger(accounts):
    badger_system = main()

    # Distribute Test Assets

    return badger_system


def distribute_from_whales(badger, recipient):
    print(len(whale_registry.items()))
    for key, whale in whale_registry.items():
        print(whale.token)
        if whale.token:
            token = interface.IERC20(whale.token)
            token.transfer(
                recipient, token.balanceOf(whale.whale), {"from": whale.whale}
            )


def distribute_rewards_escrow(badger, token, recipient, amount):
    """
    Distribute Badger from rewardsEscrow
    """

    # Approve recipient for expenditure
    if not badger.rewardsEscrow.isApproved(recipient):
        exec_direct(
            badger.devMultisig,
            {
                "to": badger.rewardsEscrow,
                "data": badger.rewardsEscrow.approveRecipient.encode_input(recipient),
            },
            badger.deployer,
        )

    exec_direct(
        badger.devMultisig,
        {
            "to": badger.rewardsEscrow,
            "data": badger.rewardsEscrow.transfer.encode_input(
                token, recipient, amount
            ),
        },
        badger.deployer,
    )
