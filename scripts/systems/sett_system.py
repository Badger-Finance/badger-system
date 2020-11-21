from helpers.proxy_utils import deploy_proxy
from brownie import *
from helpers.constants import *
from helpers.registry import registry
from config.badger_config import sett_config
from dotmap import DotMap, pprint
from enum import Enum, auto

"""
Sett is a subsystem of badger.
Requires the BadgerDAO infrastructure & multisig to be deployed
"""

curve = registry.curve
tokens = registry.tokens


def deploy_sett(badger, token, controller, name, symbol, deployer):
    """
    Deploy Sett Instance
    """
    proxyAdmin = badger.devProxyAdmin
    governance = deployer
    keeper = deployer

    print(token, controller, governance, keeper, name, symbol)

    return deploy_proxy(
        "Sett",
        Sett.abi,
        badger.logic.Sett.address,
        proxyAdmin.address,
        badger.logic.Sett.initialize.encode_input(
            token, controller, governance, keeper, name, symbol
        ),
        deployer,
    )


def deploy_strategy(badger, strategyName, controller, params, deployer):
    governance = deployer
    strategist = deployer
    keeper = deployer
    guardian = deployer
    proxyAdmin = badger.devProxyAdmin

    if strategyName == "StrategyCurveGaugeRenBtcCrv":
        return deploy_proxy(
            "StrategyCurveGaugeRenBtcCrv",
            StrategyCurveGaugeRenBtcCrv.abi,
            badger.logic.StrategyCurveGaugeRenBtcCrv.address,
            proxyAdmin.address,
            badger.logic.StrategyCurveGaugeRenBtcCrv.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [
                    params.want,
                    params.gauge,
                    params.minter,
                    params.swap,
                    params.lpComponent,
                ],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                    params.keepCRV,
                ],
            ),
            deployer,
        )
    if strategyName == "StrategyCurveGaugeSbtcCrv":
        return deploy_proxy(
            "StrategyCurveGaugeSbtcCrv",
            StrategyCurveGaugeSbtcCrv.abi,
            badger.logic.StrategyCurveGaugeSbtcCrv.address,
            proxyAdmin.address,
            badger.logic.StrategyCurveGaugeSbtcCrv.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [
                    params.want,
                    params.gauge,
                    params.minter,
                    params.swap,
                    params.lpComponent,
                ],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                    params.keepCRV,
                ],
            ),
            deployer,
        )
    if strategyName == "StrategyCurveGaugeTbtcCrv":
        return deploy_proxy(
            "StrategyCurveGaugeTbtcCrv",
            StrategyCurveGaugeTbtcCrv.abi,
            badger.logic.StrategyCurveGaugeTbtcCrv.address,
            proxyAdmin.address,
            badger.logic.StrategyCurveGaugeTbtcCrv.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [
                    params.want,
                    params.gauge,
                    params.minter,
                    params.swap,
                    params.lpComponent,
                ],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                    params.keepCRV,
                ],
            ),
            deployer,
        )
    if strategyName == "StrategyPickleMetaFarm":
        return deploy_proxy(
            "StrategyPickleMetaFarm",
            StrategyPickleMetaFarm.abi,
            badger.logic.StrategyPickleMetaFarm.address,
            proxyAdmin.address,
            badger.logic.StrategyPickleMetaFarm.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [params.want, params.pickleJar, curve.pools.renCrv.swap, tokens.wbtc],
                params.pid,
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
            ),
            deployer,
        )
    if strategyName == "StrategyHarvestMetaFarm":
        return deploy_proxy(
            "StrategyHarvestMetaFarm",
            StrategyHarvestMetaFarm.abi,
            badger.logic.StrategyHarvestMetaFarm.address,
            proxyAdmin.address,
            badger.logic.StrategyHarvestMetaFarm.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [
                    params.want,
                    params.harvestVault,
                    params.vaultFarm,
                    params.metaFarm,
                    params.badgerTree,
                ],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
            ),
            deployer,
        )
    if strategyName == "StrategyBadgerLpMetaFarm":
        return deploy_proxy(
            "StrategyBadgerLpMetaFarm",
            StrategyBadgerLpMetaFarm.abi,
            badger.logic.StrategyBadgerLpMetaFarm.address,
            proxyAdmin.address,
            badger.logic.StrategyBadgerLpMetaFarm.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [params.want, params.geyser, badger.token],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
            ),
            deployer,
        )
    if strategyName == "StrategyBadgerRewards":
        return deploy_proxy(
            "StrategyBadgerRewards",
            StrategyBadgerRewards.abi,
            badger.logic.StrategyBadgerRewards.address,
            proxyAdmin.address,
            badger.logic.StrategyBadgerRewards.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [badger.token, params.geyser],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
            ),
            deployer,
        )


def deploy_controller(badger, deployer):
    # TODO: Change to prod config
    governance = deployer
    strategist = deployer
    keeper = deployer
    rewards = badger.dao.agent
    proxyAdmin = badger.devProxyAdmin

    print(badger.logic.Controller, proxyAdmin, governance, strategist, keeper, rewards)

    return deploy_proxy(
        "Controller",
        Controller.abi,
        badger.logic.Controller.address,
        proxyAdmin.address,
        badger.logic.Controller.initialize.encode_input(
            governance, strategist, keeper, rewards
        ),
        deployer,
    )


def deploy_sett_common_logic(deployer):
    return DotMap(
        Controller=Controller.deploy({"from": deployer}),
        Sett=Sett.deploy({"from": deployer}),
        StakingRewards=StakingRewards.deploy({"from": deployer}),
    )


def deploy_sett_logic(deployer):
    return DotMap(
        StrategyCurveGauge=StrategyCurveGauge.deploy({"from": deployer}),
        StrategyPickleMetaFarm=StrategyPickleMetaFarm.deploy({"from": deployer}),
        StrategyHarvestMetaFarm=StrategyHarvestMetaFarm.deploy({"from": deployer}),
        StrategyBadgerLpMetaFarm=StrategyBadgerLpMetaFarm.deploy({"from": deployer}),
        StrategyBadgerRewards=StrategyBadgerRewards.deploy({"from": deployer}),
        Controller=Controller.deploy({"from": deployer}),
        Sett=Sett.deploy({"from": deployer}),
        StakingRewards=StakingRewards.deploy({"from": deployer}),
    )


def configure_sett(sett, deployer):
    want = sett.strategy.want()

    sett.controller.setVault(want, sett.sett, {"from": deployer})

    sett.controller.approveStrategy(
        want, sett.strategy, {"from": deployer},
    )

    sett.controller.setStrategy(
        want, sett.strategy, {"from": deployer},
    )


def deploy_sett_native_badger(badger, deployer):
    badger.add_controller("native")
    badger.add_sett("native")
    sett = DotMap(logic=deploy_sett_common_logic(deployer))
    sett.logic.StrategyBadgerRewards = StrategyBadgerRewards.deploy({"from": deployer})

    sett.controller = deploy_controller(badger, sett, deployer)

    sett.sett = deploy_sett(
        badger,
        sett,
        badger.token,
        sett.controller,
        "Badger Sett badger",
        "bBadger",
        deployer,
    )

    sett.rewards = deploy_proxy(
        "StakingRewards",
        StakingRewards.abi,
        sett.logic.StakingRewards.address,
        badger.devProxyAdmin.address,
        sett.logic.StakingRewards.initialize.encode_input(
            deployer, badger.token, badger.token
        ),
        deployer,
    )

    params = sett_config.native.badger.params
    params.want = badger.token
    params.geyser = sett.rewards

    sett.strategy = deploy_strategy(
        badger, sett, "StrategyBadgerRewards", sett.controller, params, deployer,
    )

    sett.want = interface.IERC20(sett.strategy.want())

    configure_sett(sett, deployer)

    # Approve Setts on specific
    sett.rewards.grantRole(APPROVED_STAKER_ROLE, sett.strategy, {"from": deployer})

    return sett


def deploy_sett_native_renbtc(badger, deployer):
    sett = DotMap(logic=deploy_sett_common_logic(deployer))
    sett.logic.StrategyCurveGauge = StrategyCurveGauge.deploy({"from": deployer})

    sett.controller = deploy_controller(badger, sett, deployer)

    sett.sett = deploy_sett(
        badger,
        sett,
        sett_config.native.renCrv.params.want,
        sett.controller,
        "Badger Sett renCrv",
        "bRenCrv",
        deployer,
    )

    sett.strategy = deploy_strategy(
        badger,
        sett,
        "StrategyCurveGauge",
        sett.controller,
        sett_config.native.renCrv.params,
        deployer,
    )

    sett.want = interface.IERC20(sett.strategy.want())

    configure_sett(sett, deployer)

    return sett


def deploy_sett_native_sbtccrv(badger, deployer):
    sett = DotMap(logic=deploy_sett_common_logic(deployer))
    sett.logic.StrategyCurveGauge = StrategyCurveGauge.deploy({"from": deployer})

    sett.controller = deploy_controller(badger, sett, deployer)

    sett.sett = deploy_sett(
        badger,
        sett,
        sett_config.native.sbtcCrv.params.want,
        sett.controller,
        "Badger Sett sbtcCrv",
        "bSbtcCrv",
        deployer,
    )

    sett.strategy = deploy_strategy(
        badger,
        sett,
        "StrategyCurveGauge",
        sett.controller,
        sett_config.native.sbtcCrv.params,
        deployer,
    )

    sett.want = interface.IERC20(sett.strategy.want())

    configure_sett(sett, deployer)

    return sett


def deploy_sett_native_tbtccrv(badger, deployer):
    sett = DotMap(logic=deploy_sett_common_logic(deployer))
    sett.logic.StrategyCurveGauge = StrategyCurveGauge.deploy({"from": deployer})
    sett.controller = deploy_controller(badger, sett, deployer)

    sett.sett = deploy_sett(
        badger,
        sett,
        sett_config.native.tbtcCrv.params.want,
        sett.controller,
        "Badger Sett tbtcCrv",
        "bTbtcCrv",
        deployer,
    )

    sett.strategy = deploy_strategy(
        badger,
        sett,
        "StrategyCurveGauge",
        sett.controller,
        sett_config.native.tbtcCrv.params,
        deployer,
    )

    sett.want = interface.IERC20(sett.strategy.want())

    configure_sett(sett, deployer)

    return sett


def deploy_sett_harvest_renbtc(badger, deployer):
    sett = DotMap(logic=deploy_sett_common_logic(deployer))
    sett.logic.StrategyHarvestMetaFarm = StrategyHarvestMetaFarm.deploy(
        {"from": deployer}
    )
    sett.controller = deploy_controller(badger, sett, deployer)

    sett.sett = deploy_sett(
        badger,
        sett,
        sett_config.harvest.renCrv.params.want,
        sett.controller,
        "Badger SuperSett renCrv (Harvest)",
        "bSuperRenCrv (Harvest)",
        deployer,
    )

    params = sett_config.harvest.renCrv.params
    params.rewardsEscrow = badger.rewardsEscrow
    sett.strategy = deploy_strategy(
        badger,
        sett,
        "StrategyHarvestMetaFarm",
        sett.controller,
        sett_config.harvest.renCrv.params,
        deployer,
    )

    sett.want = interface.IERC20(sett.strategy.want())

    configure_sett(sett, deployer)

    return sett


def deploy_sett_pickle_renbtc(badger, deployer):
    sett = DotMap(logic=deploy_sett_common_logic(deployer))
    sett.logic.StrategyPickleMetaFarm = StrategyPickleMetaFarm.deploy(
        {"from": deployer}
    )

    sett.controller = deploy_controller(badger, sett, deployer)

    sett.sett = deploy_sett(
        badger,
        sett,
        sett_config.pickle.renCrv.params.want,
        sett.controller,
        "Badger SuperSett renCrv (Pickle)",
        "bSuperRenCrv (Pickle)",
        deployer,
    )

    params = sett_config.pickle.renCrv.params
    sett.strategy = deploy_strategy(
        badger,
        sett,
        "StrategyPickleMetaFarm",
        sett.controller,
        sett_config.pickle.renCrv.params,
        deployer,
    )

    sett.want = interface.IERC20(sett.strategy.want())

    configure_sett(sett, deployer)

    return sett


def deploy_sett_system(badger, deployer):
    proxyAdmin = badger.proxyAdmin
    deployer = badger.deployer

    # Logic
    sett = DotMap(logic=deploy_sett_logic(deployer))

    # Controllers
    sett.native.controller = deploy_controller(badger, sett, deployer)
    sett.pickle.controller = deploy_controller(badger, sett, deployer)
    sett.harvest.controller = deploy_controller(badger, sett, deployer)

    # Deploy each pair of vault and strategy
    """
    For each group of Setts (native, harvest, pickle) iterate through each vault 
    entry and deploy the Sett and starting strategy
    """

    # Deploy Setts
    sett.native.badger = deploy_sett(
        badger,
        sett,
        badger.token,
        sett.native.controller,
        "Badger Sett badger",
        "bBadger",
        deployer,
    )

    sett.native.sbtcCrv = deploy_sett(
        badger,
        sett,
        sett_config.native.sbtcCrv.params.want,
        sett.native.controller,
        "Badger Sett sbtcCrv",
        "bSbtcCrv",
        deployer,
    )

    sett.native.renCrv = deploy_sett(
        badger,
        sett,
        sett_config.native.renCrv.params.want,
        sett.native.controller,
        "Badger Sett renCrv",
        "bRenCrv",
        deployer,
    )

    sett.native.tbtcCrv = deploy_sett(
        badger,
        sett,
        sett_config.native.tbtcCrv.params.want,
        sett.native.controller,
        "Badger Sett tbtcCrv",
        "bTbtcCrv",
        deployer,
    )

    sett.pickle.renCrv = deploy_sett(
        badger,
        sett,
        sett_config.pickle.renCrv.params.want,
        sett.pickle.controller,
        "Badger SuperSett renCrv (Pickle)",
        "bSuperRenCrv (Pickle)",
        deployer,
    )

    sett.harvest.renCrv = deploy_sett(
        badger,
        sett,
        sett_config.harvest.renCrv.params.want,
        sett.harvest.controller,
        "Badger SuperSett renCrv (Harvest)",
        "bSuperRenCrv (Harvest)",
        deployer,
    )

    # Deploy Strategy Staking Rewards
    sett.rewards = DotMap()

    sett.rewards.badger = deploy_proxy(
        "StakingRewards",
        StakingRewards.abi,
        sett.logic.StakingRewards.address,
        badger.devProxyAdmin.address,
        sett.logic.StakingRewards.initialize.encode_input(
            deployer, badger.token, badger.token
        ),
        deployer,
    )

    # Deploy Strategies
    params = sett_config.native.badger.params
    params.want = badger.token
    params.geyser = sett.rewards.badger
    sett.native.strategies.badger = deploy_strategy(
        badger, sett, "StrategyBadgerRewards", sett.native.controller, params, deployer,
    )

    sett.native.strategies.sbtcCrv = deploy_strategy(
        badger,
        sett,
        "StrategyCurveGauge",
        sett.native.controller,
        sett_config.native.sbtcCrv.params,
        deployer,
    )

    sett.native.strategies.renCrv = deploy_strategy(
        badger,
        sett,
        "StrategyCurveGauge",
        sett.native.controller,
        sett_config.native.renCrv.params,
        deployer,
    )

    sett.native.strategies.tbtcCrv = deploy_strategy(
        badger,
        sett,
        "StrategyCurveGauge",
        sett.native.controller,
        sett_config.native.tbtcCrv.params,
        deployer,
    )

    params = sett_config.pickle.renCrv.params
    sett.pickle.strategies.renCrv = deploy_strategy(
        badger,
        sett,
        "StrategyPickleMetaFarm",
        sett.pickle.controller,
        sett_config.pickle.renCrv.params,
        deployer,
    )

    params = sett_config.harvest.renCrv.params
    params.rewardsEscrow = badger.rewardsEscrow
    sett.harvest.strategies.renCrv = deploy_strategy(
        badger,
        sett,
        "StrategyHarvestMetaFarm",
        sett.harvest.controller,
        sett_config.harvest.renCrv.params,
        deployer,
    )

    # Set Vaults on Controller
    sett.native.controller.setVault(
        badger.token, sett.native.badger, {"from": deployer}
    )
    sett.native.controller.setVault(
        sett_config.native.sbtcCrv.params.want, sett.native.sbtcCrv, {"from": deployer}
    )
    sett.native.controller.setVault(
        sett_config.native.renCrv.params.want, sett.native.renCrv, {"from": deployer}
    )
    sett.native.controller.setVault(
        sett_config.native.tbtcCrv.params.want, sett.native.tbtcCrv, {"from": deployer}
    )

    sett.pickle.controller.setVault(
        sett_config.pickle.renCrv.params.want, sett.pickle.renCrv, {"from": deployer}
    )

    sett.harvest.controller.setVault(
        sett_config.harvest.renCrv.params.want, sett.harvest.renCrv, {"from": deployer}
    )

    # Approve Strategies by Controller
    sett.native.controller.approveStrategy(
        badger.token, sett.native.strategies.badger, {"from": deployer}
    )
    sett.native.controller.approveStrategy(
        sett_config.native.sbtcCrv.params.want,
        sett.native.strategies.sbtcCrv,
        {"from": deployer},
    )
    sett.native.controller.approveStrategy(
        sett_config.native.renCrv.params.want,
        sett.native.strategies.renCrv,
        {"from": deployer},
    )
    sett.native.controller.approveStrategy(
        sett_config.native.tbtcCrv.params.want,
        sett.native.strategies.tbtcCrv,
        {"from": deployer},
    )

    sett.pickle.controller.approveStrategy(
        sett_config.pickle.renCrv.params.want,
        sett.pickle.strategies.renCrv,
        {"from": deployer},
    )

    sett.harvest.controller.approveStrategy(
        sett_config.harvest.renCrv.params.want,
        sett.harvest.strategies.renCrv,
        {"from": deployer},
    )

    # Set strategies on Controller
    sett.native.controller.setStrategy(
        badger.token, sett.native.strategies.badger, {"from": deployer}
    )
    sett.native.controller.setStrategy(
        sett_config.native.sbtcCrv.params.want,
        sett.native.strategies.sbtcCrv,
        {"from": deployer},
    )
    sett.native.controller.setStrategy(
        sett_config.native.renCrv.params.want,
        sett.native.strategies.renCrv,
        {"from": deployer},
    )
    sett.native.controller.setStrategy(
        sett_config.native.tbtcCrv.params.want,
        sett.native.strategies.tbtcCrv,
        {"from": deployer},
    )

    sett.pickle.controller.setStrategy(
        sett_config.pickle.renCrv.params.want,
        sett.pickle.strategies.renCrv,
        {"from": deployer},
    )

    sett.harvest.controller.setStrategy(
        sett_config.harvest.renCrv.params.want,
        sett.harvest.strategies.renCrv,
        {"from": deployer},
    )

    # Approve Setts on specific
    sett.rewards.badger.grantRole(
        APPROVED_STAKER_ROLE, sett.native.strategies.badger, {"from": deployer}
    )

    return sett


def deploy_lp_rewards(token):
    """
    Deploy LP rewards Strategy for given Badger<>X LP Token
    """
