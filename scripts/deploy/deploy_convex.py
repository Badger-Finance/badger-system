import time

from brownie import (
    accounts,
    network,
    SettV4,
    StrategyConvexStakingOptimizer,
    AdminUpgradeabilityProxy,
)

from config.badger_config import sett_config
from rich.console import Console

import click

console = Console()

sleep_between_tx = 1

CRV_STRATS = [
    "native.renCrv",
    "native.sbtcCrv",
    "native.tbtcCrv",
    "native.hbtcCrv",
    "native.pbtcCrv",
    "native.obtcCrv",
    "native.bbtcCrv",
    "native.tricrypto2",
]

STAKING_OPTIMIZER_LOGIC = "0x0bB87f40D4eb6066a2311B7BE3B45A3D15771557"

def main():

    dev = accounts.at("0xeE8b29AA52dD5fF2559da2C50b1887ADee257556", force=True) #connect_account()

    governance = dev.address  # ops_deployer2
    strategist = "0xB65cef03b9B89f99517643226d76e286ee999e77" # Governance
    keeper = "0x711A339c002386f9db409cA55b6A35a604aB6cF6" # Keeper_acl
    guardian = "0x6615e67b8B6b6375D38A0A3f937cd8c1a1e96386" # WarRoom
    proxyAdmin = "0x20Dce41Acca85E8222D6861Aa6D23B6C941777bF" # proxyAdminTimelock
    controller = "0xe505F7C2FFcce7Ae4b076456BC02A70D8fe8d4d2"  # Test
    badgerTree = "0x660802Fc641b154aBA66a62137e71f331B6d787A"

    for strategy_key in CRV_STRATS:
        if strategy_key == "native.renCrv":
            params = sett_config.native.convexRenCrv.params
        if strategy_key == "native.sbtcCrv":
            params = sett_config.native.convexSbtcCrv.params
        if strategy_key == "native.tbtcCrv":
            params = sett_config.native.convexTbtcCrv.params
        if strategy_key == "native.hbtcCrv":
            params = sett_config.native.convexHbtcCrv.params
        if strategy_key == "native.pbtcCrv":
            params = sett_config.native.convexPbtcCrv.params
        if strategy_key == "native.obtcCrv":
            params = sett_config.native.convexObtcCrv.params
        if strategy_key == "native.bbtcCrv":
            params = sett_config.native.convexBbtcCrv.params
        if strategy_key == "native.tricrypto2":
            params = sett_config.native.convexTriCryptoDos.params

        # Deploy Vaults and Strategies
        deploy_vaults_and_strategies(
            controller,
            governance,
            strategist,
            keeper,
            guardian,
            badgerTree,
            proxyAdmin,
            params,
            strategy_key,
            dev,
        )

    print("Balance of Dev: ", dev.balance())



def deploy_vaults_and_strategies(
    controller,
    governance,
    strategist,
    keeper,
    guardian,
    badgerTree,
    proxyAdmin,
    params,
    key,
    dev,
):

    console.print("[blue]Deploying Vault for[/blue] " + key)

    # Deploy Vault

    args = [
        params.want,
        controller,
        governance,
        keeper,
        guardian,
        False,
        "",
        "",
    ]

    print("Vault Arguments: ", args)

    vault_logic = "0xA762292A6A7fD944Db1Fe9389921e6F639B4C9E8"  # SettV4 Logic

    # Deploy uninitialized proxy
    vault_proxy = AdminUpgradeabilityProxy.deploy(
        vault_logic,
        proxyAdmin,
        bytes("", encoding = "UTF-8"),
        {"from": dev},
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(vault_proxy)
    vault_proxy = SettV4.at(vault_proxy.address)

    # Initialize proxy
    vault_proxy.initialize(*args, {"from": dev})

    console.print("[green]Vault was deployed and initialized at: [/green]", vault_proxy.address)

    assert vault_proxy.paused()
    vault_proxy.unpause({"from": dev})

    # A few checks to confirm initialization
    assert vault_proxy.governance() == dev.address
    assert vault_proxy.controller() == controller
    assert vault_proxy.token() == params.want

    console.print("[blue]Deploying Strategy for[/blue] " + key)

    # Deploy Strategy

    args = [
        governance,
        strategist,
        controller,
        keeper,
        guardian,
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

    strat_proxy = AdminUpgradeabilityProxy.deploy(
        STAKING_OPTIMIZER_LOGIC,
        proxyAdmin,
        bytes("", encoding = "UTF-8"),
        {"from": dev},
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(strat_proxy)
    strat_proxy = StrategyConvexStakingOptimizer.at(strat_proxy.address)

    # Initialize proxy
    strat_proxy.initialize(*args, {"from": dev})

    # A few checks to confirm initialization
    assert strat_proxy.crvCvxCrvSlippageToleranceBps() == 500
    assert strat_proxy.withdrawalFee() == 50
    assert strat_proxy.performanceFeeGovernance() == 1000
    assert strat_proxy.performanceFeeStrategist() == 0
    assert strat_proxy.governance() == dev.address
    assert strat_proxy.controller() == controller

    console.print("[green]Strategy was deployed and initialized at: [/green]", strat_proxy.address)

    return strat_proxy

def connect_account():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")
    return dev
