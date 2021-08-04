from assistant.subgraph.client import fetch_sett_balances, fetch_wallet_balances
from assistant.rewards.rewards_utils import calculate_sett_balances
from scripts.systems.badger_system import connect_badger
import json


def main():
    block = 12428803
    badger = connect_badger()

    bbadger = list(
        calculate_sett_balances(badger, "native.badger", block).userBalances.keys()
    )

    uniBadger = list(
        calculate_sett_balances(
            badger, "native.uniBadgerWbtc", block
        ).userBalances.keys()
    )

    sushiBadger = list(
        calculate_sett_balances(
            badger, "native.sushiBadgerWbtc", block
        ).userBalances.keys()
    )

    badger_holders, digg_holders = fetch_wallet_balances(1, 1, badger.digg, block)

    with open("badger_holders.json", "w") as fp:
        json.dump(
            list(
                set([*bbadger, *uniBadger, *sushiBadger, *list(badger_holders.keys())])
            ),
            fp,
        )
