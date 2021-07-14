import time

from brownie import accounts, MStableVoterProxy

from scripts.systems.badger_system import connect_badger
from scripts.systems.mstable_system import MStableSystem
from config.badger_config import sett_config
from helpers.registry import registry
from dotmap import DotMap
from rich.console import Console

console = Console()

sleep_between_tx = 1

def main():
    badger = connect_badger("deploy-final.json")

    dualGovernance = accounts.at("0xFa333CC67ac84e687133Ec707D1948E6F4b2b7c5", force=True)
    deployer = badger.deployer
    controller = badger.getController("native")
    governance = badger.devMultisig
    strategist = badger.deployer
    keeper = badger.keeper
    guardian = badger.guardian

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

    mstable = MStableSystem(deployer, badger.devProxyAdmin, mstable_config)
    mstable.deploy_logic("MStableVoterProxy", MStableVoterProxy)
    time.sleep(sleep_between_tx)
    mstable.deploy_voterproxy()
    time.sleep(sleep_between_tx)

    console.print(
        "[green]VoterProxy was deployed at: [/green]", mstable.voterproxy.address
    )

    # Deploy Vaults and Strategies
    
    for (key, strategyName) in [
        ("native.mstableImBtc", "StrategyMStableVaultImbtc"),
        ("native.mstableFpMbtcHbtc", "StrategyMStableVaultFpMbtcHbtc"),
    ]:
        if key == "native.mstableImBtc":
            params = sett_config.native.imBtc.params
            want = sett_config.native.imBtc.params.want
        else:
            params = sett_config.native.fPmBtcHBtc.params
            want = sett_config.native.fPmBtcHBtc.params.want
        
        params.badgerTree = badger.badgerTree

        vault = badger.deploy_sett(
            key,
            want,
            controller,
            governance=governance,
            strategist=strategist,
            keeper=keeper,
            guardian=guardian,
        )
        time.sleep(sleep_between_tx)

        console.print(
            "[green]Vault was deployed at: [/green]", vault.address
        )

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

        console.print(
            "[green]Strategy was deployed at: [/green]", strategy.address
        )

        badger.wire_up_sett(vault, strategy, controller)

        # Confirm wire-up
        assert controller.strategies(vault.token()) == strategy.address
        assert controller.vaults(strategy.want()) == vault.address

        assert vault.paused()
