from brownie import *
from rich.console import Console

from helpers.registry import registry
from helpers.proxy_utils import deploy_proxy

console = Console()

"""
Sett is a subsystem of badger.
Requires the BadgerDAO infrastructure & multisig to be deployed
"""

curve = registry.curve
tokens = registry.tokens


def deploy_strategy(
    badger,
    strategyName,
    controller,
    params,
    deployer,
    governance=None,
    strategist=None,
    keeper=None,
    guardian=None,
):
    if not governance:
        governance = deployer

    if not strategist:
        strategist = deployer

    if not keeper:
        keeper = badger.keeper

    if not guardian:
        guardian = badger.guardian

    proxyAdmin = badger.devProxyAdmin

    console.print("Deploy Strategy " + strategyName, params)

    if strategyName == "StrategyUnitProtocolRenbtc":
        return deploy_proxy(
            "StrategyUnitProtocolRenbtc",
            StrategyUnitProtocolRenbtc.abi,
            badger.logic.StrategyUnitProtocolRenbtc.address,
            proxyAdmin.address,
            badger.logic.StrategyUnitProtocolRenbtc.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [
                    params.want,
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
    if strategyName == "StrategyDiggRewards":
        return deploy_proxy(
            "StrategyDiggRewards",
            StrategyDiggRewards.abi,
            badger.logic.StrategyDiggRewards.address,
            proxyAdmin.address,
            badger.logic.StrategyDiggRewards.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [params.want, params.geyser,],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
            ),
            deployer,
        )
    if strategyName == "StrategySushiLpOptimizer":
        return deploy_proxy(
            "StrategySushiLpOptimizer",
            StrategySushiLpOptimizer.abi,
            badger.logic.StrategySushiLpOptimizer.address,
            proxyAdmin.address,
            badger.logic.StrategySushiLpOptimizer.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [params.want, params.badgerTree,],
                params.pid,
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
            ),
            deployer,
        )
    if strategyName == "StrategySushiBadgerWbtc":
        return deploy_proxy(
            "StrategySushiBadgerWbtc",
            StrategySushiBadgerWbtc.abi,
            badger.logic.StrategySushiBadgerWbtc.address,
            proxyAdmin.address,
            badger.logic.StrategySushiBadgerWbtc.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [params.want, params.geyser, params.badger, params.badgerTree],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
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
    if strategyName == "StrategySushiDiggWbtcLpOptimizer":
        return deploy_proxy(
            "StrategySushiDiggWbtcLpOptimizer",
            StrategySushiDiggWbtcLpOptimizer.abi,
            badger.logic.StrategySushiDiggWbtcLpOptimizer.address,
            proxyAdmin.address,
            badger.logic.StrategySushiDiggWbtcLpOptimizer.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [params.want, params.geyser, params.token, params.badgerTree,],
                params.pid,
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
            ),
            deployer,
        )
    if strategyName == "StrategyDiggLpMetaFarm":
        return deploy_proxy(
            "StrategyDiggLpMetaFarm",
            StrategyDiggLpMetaFarm.abi,
            badger.logic.StrategyDiggLpMetaFarm.address,
            proxyAdmin.address,
            badger.logic.StrategyDiggLpMetaFarm.initialize.encode_input(
                governance,
                strategist,
                controller,
                keeper,
                guardian,
                [params.want, params.geyser, params.token,],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
            ),
            deployer,
        )
    if strategyName == "StrategyPancakeLpOptimizer":
        return deploy_proxy(
            "StrategyPancakeLpOptimizer",
            StrategyPancakeLpOptimizer.abi,
            badger.logic.StrategyPancakeLpOptimizer.address,
            badger.devProxyAdmin.address,
            badger.logic.StrategyPancakeLpOptimizer.initialize.encode_input(
                badger.devMultisig,
                badger.deployer,
                controller,
                badger.keeper,
                badger.guardian,
                [params.want, params.token0, params.token1,],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
                params.pid,
            ),
            badger.deployer,
        )
    if strategyName == "StrategyUniGenericLp":
        return deploy_proxy(
            "StrategyUniGenericLp",
            StrategyUniGenericLp.abi,
            badger.logic.StrategyUniGenericLp.address,
            badger.devProxyAdmin.address,
            badger.logic.StrategyUniGenericLp.initialize.encode_input(
                badger.devMultisig,
                badger.deployer,
                controller,
                badger.keeper,
                badger.guardian,
                [params.want,],
                [params.withdrawalFee,],
            ),
            badger.deployer,
        )
    if strategyName == "StrategyPancakeLpOptimizer":
        return deploy_proxy(
            "StrategyPancakeLpOptimizer",
            StrategyPancakeLpOptimizer.abi,
            badger.logic.StrategyPancakeLpOptimizer.address,
            badger.devProxyAdmin.address,
            badger.logic.StrategyPancakeLpOptimizer.initialize.encode_input(
                badger.devMultisig,
                badger.deployer,
                controller,
                badger.keeper,
                badger.guardian,
                [params.want, params.token0, params.token1,],
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
                params.pid,
            ),
            badger.deployer,
        )


def deploy_controller(
    badger,
    deployer,
    governance=None,
    strategist=None,
    keeper=None,
    rewards=None,
    proxyAdmin=None,
):
    # TODO: Change to prod config

    # Set default roles if not specified
    if not governance:
        governance = deployer
    if not strategist:
        strategist = deployer
    if not keeper:
        keeper = badger.keeper
    if not rewards:
        rewards = badger.keeper
    if not proxyAdmin:
        proxyAdmin = badger.devProxyAdmin

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
