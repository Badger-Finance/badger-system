import time

from brownie import (
    accounts,
    network,
    SettV4, 
    StrategyConvexStakingOptimizer,
    AdminUpgradeabilityProxy,
)
from config.badger_config import sett_config
from dotmap import DotMap
from rich.console import Console

import click

console = Console()

sleep_between_tx = 1

def main():

    dev = connect_account()

    governance = accounts.at("0xB65cef03b9B89f99517643226d76e286ee999e77", force=True) # devMultisig
    strategist = accounts.at("0xDA25ee226E534d868f0Dd8a459536b03fEE9079b", force=True) # deployer
    keeper = accounts.at("0x872213E29C85d7e30F1C8202FC47eD1Ec124BB1D", force=True)
    guardian = accounts.at("0x29F7F8896Fb913CF7f9949C623F896a154727919", force=True)
    devProxyAdmin = accounts.at("0x20Dce41Acca85E8222D6861Aa6D23B6C941777bF", force=True)

    controller = "0x9b4efA18c0c6b4822225b81D150f3518160f8609" # Experimental
    badgerTree = "0x660802Fc641b154aBA66a62137e71f331B6d787A"

    # Deploy Vaults and Strategies
    deploy_vaults_and_strategies(
        controller, 
        governance, 
        strategist, 
        keeper, 
        guardian, 
        badgerTree, 
        devProxyAdmin, 
        dev
    )

    print("Balance of Dev: ", dev.balance())
    

def deploy_vaults_and_strategies(
    controller, 
    governance, 
    strategist, 
    keeper, 
    guardian, 
    badgerTree, 
    devProxyAdmin, 
    dev
):
    # Deploy Vaults and Strategies    
    params = sett_config.native.convexTriCryptoDos.params
    want = sett_config.native.convexTriCryptoDos.params.want

    print("Deploying Vault and Strategy for Tricrypto2 Convex")

    # Deploy Vault

    args = [
        want,
        controller,
        governance.address,
        keeper.address,
        guardian.address,
        False,
        '',
        '',
    ]

    print("Vault Arguments: ", args)

    vault_logic = SettV4.at("0xA762292A6A7fD944Db1Fe9389921e6F639B4C9E8") # SettV4 Logic
    time.sleep(sleep_between_tx)

    vault_proxy = AdminUpgradeabilityProxy.deploy(
        vault_logic, 
        devProxyAdmin, 
        vault_logic.initialize.encode_input(*args), 
        {'from': dev}
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(vault_proxy)
    vault_proxy = SettV4.at(vault_proxy.address)

    console.print(
        "[green]Vault was deployed at: [/green]", vault_proxy.address
    )

    assert vault_proxy.paused()

    # Deploy Strategy

    args = [
        governance.address,
        strategist.address,
        controller,
        keeper.address,
        guardian.address,
        [
            params.want,
            badgerTree,
            params.cvxHelperVault,
            params.cvxCrvHelperVault,
        ],
        params.pid,
        [
            params.performanceFeeGovernance,
            params.performanceFeeStrategist,
            params.withdrawalFee,
        ],
        (
            params.curvePool.swap,
            params.curvePool.wbtcPosition,
            params.curvePool.numElements,
        ),
    ]

    print("Strategy Arguments: ", args)

    strat_logic = StrategyConvexStakingOptimizer.deploy({"from": dev})
    time.sleep(sleep_between_tx)
    # Verify on Etherscan
    # strat_logic.publish_source(artifact)

    strat_proxy = AdminUpgradeabilityProxy.deploy(
        strat_logic, 
        devProxyAdmin, 
        strat_logic.initialize.encode_input(*args), 
        {'from': dev}
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(strat_proxy)
    strat_proxy = StrategyConvexStakingOptimizer.at(strat_proxy.address)

    console.print(
        "[green]Strategy was deployed at: [/green]", strat_proxy.address
    )


def connect_account():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")
    return dev