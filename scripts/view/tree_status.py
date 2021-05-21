from helpers.token_utils import print_balances, to_token
from brownie import *
from config.badger_config import badger_config
from helpers.time_utils import hours, to_utc_date
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from helpers.registry import registry


def main():
    badger = connect_badger(badger_config.prod_json)

    table = []

    tree = badger.badgerTree
    lastPublish = tree.lastPublishTimestamp()
    timeSinceLastPublish = chain.time() - lastPublish

    table.append(["now", to_utc_date(chain.time())])
    table.append(["---------------", "--------------------"])
    table.append(["lastPublishTimestamp", lastPublish])
    table.append(["lastPublishDate", to_utc_date(lastPublish)])
    table.append(["---------------", "--------------------"])
    table.append(["secondsSinceLastPublish", timeSinceLastPublish])
    table.append(["hoursSinceLastPublish", timeSinceLastPublish / 3600])

    print(tabulate(table, headers=["metric", "value"]))

    table = []

    print_balances(["badger", "digg", "farm", "xSushi"], tree)
