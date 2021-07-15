import time

from brownie import (
    accounts,
    network,
    web3,
    MStableVoterProxy, 
    SettV3, 
    StrategyMStableVaultImbtc, 
    StrategyMStableVaultFpMbtcHbtc, 
)

from scripts.systems.badger_system import connect_badger
from scripts.systems.mstable_system import MStableSystem
from config.badger_config import sett_config
from helpers.registry import registry
from dotmap import DotMap
from rich.console import Console
from helpers.registry.artifacts import artifacts

import click

console = Console()

sleep_between_tx = 1

def main():
    badger = connect_badger("deploy-final.json")

    dev = connect_account()

    dualGovernance = accounts.at("0xFa333CC67ac84e687133Ec707D1948E6F4b2b7c5", force=True)
    controller = badger.getController("experimental")
    governance = badger.devMultisig
    strategist = badger.deployer
    keeper = badger.keeper
    guardian = badger.guardian

    # Deploy voterProxy
    voterproxy = deploy_voterProxy(badger, dev, dualGovernance, governance, strategist, keeper)

    # Deploy Vaults and Strategies
    deploy_vaults_and_strategies(controller, governance, strategist, keeper, guardian, voterproxy, badger, dev)


    

def deploy_vaults_and_strategies(controller, governance, strategist, keeper, guardian, voterproxy, badger, dev):
    # Deploy Vaults and Strategies
    abi = artifacts.open_zeppelin["AdminUpgradeabilityProxy"]["abi"]
    bytecode = artifacts.open_zeppelin["AdminUpgradeabilityProxy"]["bytecode"]

    AdminUpgradeabilityProxy = web3.eth.contract(abi=abi, bytecode=bytecode)
    
    for (key, artifact) in [
        ("native.mstableImBtc", StrategyMStableVaultImbtc),
        ("native.mstableFpMbtcHbtc", StrategyMStableVaultFpMbtcHbtc),
    ]:
        if key == "native.mstableImBtc":
            params = sett_config.native.imBtc.params
            want = sett_config.native.imBtc.params.want
        else:
            params = sett_config.native.fPmBtcHBtc.params
            want = sett_config.native.fPmBtcHBtc.params.want
        
        params.badgerTree = badger.badgerTree

        print("Deploying Vault and Strategy for " + key)

        print("Vault Arguments: ", args)

        # Deploy Vault

        args = [
            want,
            controller,
            governance,
            keeper,
            guardian,
            False,
            '',
            '',
        ]

        vault_logic = SettV3.deploy({"from": dev})
        vault_proxy = AdminUpgradeabilityProxy.deploy(vault_logic, badger.proxyAdmin, vault_logic.initialize.encode_input(*args), {'from': dev})

        ## We delete from deploy and then fetch again so we can interact
        AdminUpgradeabilityProxy.remove(vault_proxy)
        vault_proxy = SettV3.at(vault_proxy.address)

        console.print(
            "[green]Vault was deployed at: [/green]", vault_proxy.address
        )
        time.sleep(sleep_between_tx)

        assert vault_proxy.paused()

        # Deploy Strategy

        args = [
            governance,
            strategist,
            controller,
            keeper,
            guardian,
            [
                params.want,
                params.vault,
                voterproxy.address,
                params.lpComponent,
                params.badgerTree,
            ],
            [
                params.performanceFeeGovernance,
                params.performanceFeeStrategist,
                params.withdrawalFee,
                params.govMta,
            ],
        ]

        print("Strategy Arguments: ", args)

        strat_logic = artifact.deploy({"from": dev})
        # Verify on Etherscan
        strat_logic.publish_source(artifact)
        strat_proxy = AdminUpgradeabilityProxy.deploy(vault_logic, badger.proxyAdmin, strat_logic.initialize.encode_input(*args), {'from': dev})

        ## We delete from deploy and then fetch again so we can interact
        AdminUpgradeabilityProxy.remove(strat_proxy)
        strat_proxy = SettV3.at(strat_proxy.address)

        console.print(
            "[green]Strategy was deployed at: [/green]", strat_proxy.address
        )



def deploy_voterProxy(badger, dev, dualGovernance, governance, strategist, keeper):
    # Deploy VoterProxy

    mstable_config = DotMap(
        dualGovernance=dualGovernance,
        badgerGovernance=governance,
        strategist=strategist,
        keeper=keeper,
        configAddress1=registry.mstable.nexus,
        configAddress2=registry.mstable.votingLockup,
        rates=8000,
    )

    mstable = MStableSystem(dev, badger.devProxyAdmin, mstable_config)

    mstable.deploy_logic("MStableVoterProxy", MStableVoterProxy)
    time.sleep(sleep_between_tx)

    # Verify Contract
    mstable.logic["MStableVoterProxy"].publish_source(MStableVoterProxy)

    mstable.deploy_voterproxy()
    time.sleep(sleep_between_tx)

    console.print(
        "[green]VoterProxy was deployed at: [/green]", mstable.voterproxy.address
    )

    return mstable.voterproxy


def connect_account():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")
    return dev
