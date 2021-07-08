import time

from scripts.systems.badger_system import connect_badger
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.uniswap_system import UniswapSystem
from config.badger_config import sett_config
from helpers.registry import registry

sleep_between_tx = 1


def main():

    badger = connect_badger("deploy-final.json")

    deployer = badger.deployer
    controller = badger.getController("native")
    governance = badger.devMultisig
    strategist = badger.deployer
    keeper = badger.keeper
    guardian = badger.guardian

    for (key, strategyName, isUniswap) in [
        ("native.sushiWbtcIbBtc", "StrategySushiLpOptimizer", False),
        # ("native.uniWbtcIbBtc", "StrategyUniGenericLp", True),
    ]:
        if isUniswap:
            params = sett_config.uni.uniGenericLp.params
            swap = UniswapSystem()
        else:
            params = sett_config.sushi.sushiWbtcIbBtc.params
            params.badgerTree = badger.badgerTree

            swap = SushiswapSystem()

        if swap.hasPair(registry.tokens.ibbtc, registry.tokens.wbtc):
            params.want = swap.getPair(registry.tokens.ibbtc, registry.tokens.wbtc)
        else:
            params.want = swap.createPair(
                registry.tokens.ibbtc, registry.tokens.wbtc, deployer,
            )

        # NB: Work w/ sushi team to setup sushi reward allocations.

        vault = badger.deploy_sett(
            key,
            params.want,
            controller,
            governance=governance,
            strategist=strategist,
            keeper=keeper,
            guardian=guardian,
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

        badger.wire_up_sett(vault, strategy, controller)

        # TODO: Unpause vault.
        assert vault.paused()
