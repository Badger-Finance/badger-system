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


def main():
    badger = connect_badger(badger_config.prod_json)
    badger.upgrade_strategy_native_rencrv()
