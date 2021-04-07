from rich.console import Console

from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger

console = Console()


def test_upgrade():
    # connect to prod deploy and run simulation
    console.print("[grey]connecting to badger system...[/grey]")
    badger = connect_badger(badger_config.prod_json)

    console.print("[grey]upgrading sett contracts...[/grey]")
    badger.upgrade.upgrade_sett_contracts(validate=True)

    console.print("[grey]upgrading strategy contracts...[/grey]")
    badger.upgrade.upgrade_strategy_contracts(validate=True)

    console.print("[green]sett/strategy contracts upgraded[/green]")
