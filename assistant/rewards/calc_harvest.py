from collections import Counter
from assistant.rewards.User import User
from rich.console import Console

console = Console()
def get_initial_user_state(settBalances,geyserBalances, startBlockTime):
    balances = combine_balances(settBalances,geyserBalances)
    users = []
    for addr, balance in balances.items():
        users.append(User(addr, balance, startBlockTime))
    return users


def calc_balances_from_geyser_events(geyserEvents):
    balances = {}
    events = [*geyserEvents["stakes"], *geyserEvents["unstakes"]]
    events = sorted(events, key=lambda e: e["timestamp"])
    currentTime = 0
    for event in events:
        timestamp = int(event["timestamp"])
        assert timestamp >= currentTime
        balances[event["user"]] = int(event["total"])

    console.log("Sum of geyser balances: {}".format(sum(balances.values()) / 10 ** 18))
    return balances


def combine_balances(settBalances, geyserBalances):
    return dict(Counter(settBalances) + Counter(geyserBalances))

