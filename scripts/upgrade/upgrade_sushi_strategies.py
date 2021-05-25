from rich.console import Console

from config.badger_config import badger_config
from helpers.sett.strategy_registry import name_to_artifact
from scripts.systems.badger_system import BadgerSystem, connect_badger

console = Console()


SUSHI_STRATEGIES_TO_UPGRADE = [
    ("native.sushiBadgerWbtc", "StrategySushiBadgerWbtc"),
    ("native.sushiDiggWbtc", "StrategySushiDiggWbtcLpOptimizer"),
]


def queue_upgrade_strategy(
    badger: BadgerSystem,
    strategyID: str,
    artifactName: str,
) -> str:
    badger.deploy_logic(artifactName, name_to_artifact[artifactName])
    logic = badger.logic[artifactName]
    return badger.queue_upgrade_strategy(strategyID, logic)


def main():
    """
    Queues sushi strategies for upgrade:
     - Remove harvesting of obsolete staking rewards pool
     - Remove associated auto-compounding logic (now handled externally)
    """
    badger = connect_badger(badger_config.prod_json)

    for (strategyID, artifactName) in SUSHI_STRATEGIES_TO_UPGRADE:
        txFilename = queue_upgrade_strategy(badger, strategyID, artifactName)
        console.print("[orange] queued up timelock tx {} [/orange]".format(txFilename))
