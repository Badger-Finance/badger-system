from brownie import (
    StrategyCurveGaugeRenBtcCrv,
    StrategyCurveGaugeSbtcCrv,
    StrategyCurveGaugeTbtcCrv,
    network,
)
from rich.console import Console

from scripts.systems.badger_system import BadgerSystem, connect_badger
from config.badger_config import badger_config

console = Console()

def upgrade_crv_strategy(
    badger: BadgerSystem,
    previous: network.contract.ProjectContract,
    Strategy: network.contract.ContractContainer,
) -> str:
    """
    Upgrades swap strategy.
    """
    logic = Strategy.deploy({"from": badger.deployer})
    return badger.queue_upgrade_sett(
        previous.address,
        logic.address,
    )


def main():
    badger = connect_badger(badger_config.prod_json)

    previousRenBTCStrat = badger.getStrategy("native.renCrv")
    upgrade_crv_strategy(badger, previousRenBTCStrat, StrategyCurveGaugeRenBtcCrv)
    console.print("[orange]Queued swap strategy update for RenCRV[/orange]")

        
    previousSBTCStrat = badger.getStrategy("native.sbtcCrv")
    upgrade_crv_strategy(badger, previousSBTCStrat, StrategyCurveGaugeSbtcCrv)
    console.print("[orange]Queued swap strategy update for sBTCCRV[/orange]")

    previousTBTCStrat = badger.getStrategy("native.tbtcCrv")
    upgrade_crv_strategy(badger, previousTBTCStrat, StrategyCurveGaugeTbtcCrv)
    console.print("[orange]Queued swap strategy update for tBTCCurve[/orange]")
