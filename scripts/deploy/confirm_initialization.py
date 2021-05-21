from brownie import *
from config.badger_config import badger_config
from dotmap import DotMap
from helpers.constants import *
from helpers.registry import registry
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger

console = Console()

# def confirm_initialization(badger: BadgerSystem):
