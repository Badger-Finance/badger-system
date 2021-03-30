import decouple

from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.systems.sushiswap_system import SushiswapSystem
from config.badger_config import sett_config
from helpers.registry import registry

sleep_between_tx = 1

def main():

    badger = connect_badger("deploy-final.json")

    deployer = badger.deployer
    key = "native.sushiWbtcIbBtc"
    controller = badger.getController("native")
    governance = badger.devMultisig
    strategist = badger.deployer
    keeper = badger.keeper
    guardian = badger.guardian

    params = sett_config.sushi.sushiWbtcIbBtc.params
    params.badgerTree = badger.badgerTree

    sushiswap = SushiswapSystem()
    if sushiswap.hasPair(registry.tokens.ibbtc, registry.tokens.wbtc):
        params.want = sushiswap.getPair(registry.tokens.ibbtc, registry.tokens.wbtc)
    else:
        params.want = sushiswap.createPair(
            registry.tokens.ibbtc,
            registry.tokens.wbtc,
            deployer,
        )

    # Setup sushi reward allocations (ONLY DO THIS ONCE).
    params.pid = sushiswap.add_chef_rewards(params.want)

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

    assert vault.paused()
    vault.unpause({"from": governance})
    assert vault.paused() == False
