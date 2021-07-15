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

    dev = connect_account()

    dualGovernance = accounts.at("0xFa333CC67ac84e687133Ec707D1948E6F4b2b7c5", force=True)
    governance = accounts.at("0xB65cef03b9B89f99517643226d76e286ee999e77", force=True) # devMultisig
    strategist = accounts.at("0xDA25ee226E534d868f0Dd8a459536b03fEE9079b", force=True) # deployer
    keeper = accounts.at("0x872213E29C85d7e30F1C8202FC47eD1Ec124BB1D", force=True)
    guardian = accounts.at("0x29F7F8896Fb913CF7f9949C623F896a154727919", force=True)
    devProxyAdmin = accounts.at("0x20Dce41Acca85E8222D6861Aa6D23B6C941777bF", force=True)

    controller = "0x9b4efA18c0c6b4822225b81D150f3518160f8609" # Experimental
    badgerTree = "0x660802Fc641b154aBA66a62137e71f331B6d787A"


    # Deploy voterProxy
    voterproxy = deploy_voterProxy(devProxyAdmin, dev, dualGovernance, governance, strategist, keeper)

    # Deploy Vaults and Strategies
    deploy_vaults_and_strategies(
        controller, 
        governance, 
        strategist, 
        keeper, 
        guardian, 
        voterproxy, 
        badgerTree, 
        devProxyAdmin, 
        dev
    )


    

def deploy_vaults_and_strategies(
    controller, 
    governance, 
    strategist, 
    keeper, 
    guardian, 
    voterproxy, 
    badgerTree, 
    proxyAdmin, 
    dev
):
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

        print("Deploying Vault and Strategy for " + key)

        print("Vault Arguments: ", args)

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

        vault_logic = SettV3.deploy({"from": dev})
        time.sleep(sleep_between_tx)

        vault_proxy = AdminUpgradeabilityProxy.deploy(
            vault_logic, 
            proxyAdmin, 
            vault_logic.initialize.encode_input(*args), 
            {'from': dev}
        )
        time.sleep(sleep_between_tx)

        ## We delete from deploy and then fetch again so we can interact
        AdminUpgradeabilityProxy.remove(vault_proxy)
        vault_proxy = SettV3.at(vault_proxy.address)

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
                params.vault,
                voterproxy.address,
                params.lpComponent,
                badgerTree,
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
        time.sleep(sleep_between_tx)
        # Verify on Etherscan
        strat_logic.publish_source(artifact)
        time.sleep(sleep_between_tx)

        strat_proxy = AdminUpgradeabilityProxy.deploy(
            vault_logic, 
            proxyAdmin, 
            strat_logic.initialize.encode_input(*args), 
            {'from': dev}
        )
        time.sleep(sleep_between_tx)

        ## We delete from deploy and then fetch again so we can interact
        AdminUpgradeabilityProxy.remove(strat_proxy)
        strat_proxy = SettV3.at(strat_proxy.address)

        console.print(
            "[green]Strategy was deployed at: [/green]", strat_proxy.address
        )



def deploy_voterProxy(devProxyAdmin, dev, dualGovernance, governance, strategist, keeper):
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

    mstable = MStableSystem(dev, devProxyAdmin, mstable_config)

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
