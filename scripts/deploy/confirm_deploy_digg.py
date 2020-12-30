from rich.console import Console

from scripts.systems.digg_system import connect_digg
from config.badger_config import digg_config

console = Console()

"""
Ensure everything is configured as expected immediately post-deploy
"""


def confirm_setup_oracles(digg):
    pass


def confirm_setup_digg(digg):
    pass


def confirm_deploy(digg):
    confirm_setup_oracles(digg)
    confirm_setup_digg(digg)


def main():
    digg = connect_digg(digg_config.prod_json)
    confirm_deploy(digg)
