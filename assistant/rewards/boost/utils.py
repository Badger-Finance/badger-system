from assistant.rewards.classes.UserBalance import UserBalance, UserBalances
from assistant.rewards.snapshot.utils import chain_snapshot
from assistant.badger_api.prices import (
    fetch_token_prices,
)

prices = fetch_token_prices()


def calc_union_addresses(nativeSetts, nonNativeSetts):
    return set.union(
        *[
            {user.address for user in nativeSetts},
            {user.address for user in nonNativeSetts},
        ]
    )


def filter_dust(balances, dustAmount):
    """
    Filter out dust values from user balances
    """
    return UserBalances(
        list(filter(lambda user: user.balance > dustAmount, balances)),
        balances.settType,
        balances.settRatio,
    )


def convert_balances_to_usd(userBalances):
    price = prices[tokenAddress]
    priceRatio = userBalances.settRatio
    for user in userBalances:
        user.balance = settRatio * price * user.balance

    return userBalances


def calc_boost_data(badger, block):
    chains = ["eth", "bsc", "polygon", "xdai"]
    ethSnapshot = chain_snapshot("eth", badger, block)
    bscSnapshot = chain_snapshot("eth", badger, block)
    polygonSnapshot = chain_snapshot("polygon", badger, block)
    ## Figure out how to map blocks, maybe  time -> block per chain

    native = {}
    nonNative = {}

    for chain in chains:
        snapshot = chain_snapshot(chain, badger, block)
        for sett, balances in snapshot.items():
            balances = convert_balances_to_usd(balances)
            if balances.settType == "native":
                native = dict(Counter(balances) + Counter(native))
            elif balances.settType == "nonNative":
                nonNative = dict(Counter(balances) + Counter(nonNative))

    return filter_dust(UserBalances(native, "", ""), 1),
    filter_dust(UserBalances(nonNative, "", ""), 1)
