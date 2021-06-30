from config.keeper import keeper_config
from brownie import *
from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger
from assistant.rewards.boost import badger_boost
from scripts.keeper.harvest import harvest_all
from helpers.console_utils import console
from helpers.registry import registry

strats_to_upgrade = ["native.pbtcCrv", "native.obtcCrv" ,"native.pbtcCrv"]

def test_main():
    main()

def main():
    badger = connect_badger()

    new_logic = StrategyConvexStakingOptimizer.deploy({"from": badger.deployer})
    
    tm = accounts.at(badger.testMultisig.address, force=True)

    strategy = badger.getStrategy("native.pbtcCrv")
    console.print("Before", {
        "curvePool": strategy.curvePool()
    })
    badger.testProxyAdmin.upgrade(strategy, new_logic, {'from': tm})
    strategy.setCurvePoolSwap(registry.curve.pools.pbtcCrv.swap, {'from': tm})
    console.print("After", {
        "curvePool": strategy.curvePool()
    })

    strategy = badger.getStrategy("native.obtcCrv")
    # console.print("Before 2", {
    #     "curvePool": strategy.curvePool()
    # })
    # badger.testProxyAdmin.upgrade(strategy, new_logic, {'from': tm})
    strategy.setCurvePoolSwap(registry.curve.pools.obtcCrv.swap, {'from': tm})
    # console.print("After 2", {
    #     "curvePool": strategy.curvePool()
    # })

    strategy = badger.getStrategy("native.bbtcCrv")
    # console.print("Before 3", {
    #     "curvePool": strategy.curvePool()
    # })
    # badger.testProxyAdmin.upgrade(strategy, new_logic, {'from': tm})
    strategy.setCurvePoolSwap(registry.curve.pools.bbtcCrv.swap, {'from': tm})

    # console.print("After 3", {
    #     "curvePool": strategy.curvePool()
    # })

    if rpc.is_active():
        """
        Test: Load up testing accounts with ETH
        """
        accounts[0].transfer(badger.deployer, Wei("5 ether"))
        accounts[0].transfer(badger.keeper, Wei("5 ether"))
        accounts[0].transfer(badger.guardian, Wei("5 ether"))

    skip = keeper_config.get_active_chain_skipped_setts("harvest")
    harvest_all(badger, skip)
