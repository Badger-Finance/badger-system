from helpers.time_utils import hours, to_utc_date
from brownie import *
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from config.badger_config import badger_config


def main():
    badger = connect_badger(badger_config.prod_file)

    table = []

    tree = badger.badgerTree
    lastPublish = tree.lastPublishTimestamp()

    table.append(["lastPublishTimestamp", tree.lastPublish])
    table.append(["lastPublishDate", to_utc_date(lastPublish)])
    table.append(["timeSinceLastPublish", hours(chain.time() - lastPublish)])

    table.append(["---------------", "--------------------"])
    print(tabulate(table, headers=["metric", "value"]))
