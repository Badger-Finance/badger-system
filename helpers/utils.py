# Assert approximate integer
def approx(actual, expected, percentage_threshold):
    print(actual, expected, percentage_threshold)
    diff = int(abs(actual - expected))
    # 0 diff should automtically be a match
    if diff == 0:
        return True
    return diff < (actual * percentage_threshold // 100)


def Eth(value):
    return value / 1e18


def digg_shares_to_initial_fragments(digg, shares):
    """
    Convert shares to initial fragments scale
    For negative numbers (for example as part of a diff), use abs first
    """
    scaled = 0
    if shares < 0:
        shares = abs(shares)
        scaled = digg.sharesToScaledShares(shares)
        scaled = -scaled
    else:
        scaled = digg.sharesToScaledShares(shares)
    return val(scaled)


def digg_shares(value):
    return value / 1e68


def val(amount, decimals=18):
    # return amount
    # return "{:,.0f}".format(amount)
    return "{:,.18f}".format(amount / 10 ** decimals)


def sec(amount):
    return "{:,.1f}".format(amount / 1e12)


def snapBalancesMatchForToken(snap, otherSnap, tokenKey):
    for entityKey in snap.entityKeys:
        balance = snap.balances(tokenKey, entityKey)
        otherBalance = otherSnap.balances(tokenKey, entityKey)
        if balance != otherBalance:
            return False
    return True


def snapSharesMatchForToken(snap, otherSnap, tokenKey):
    for entityKey in snap.entityKeys:
        shares = snap.shares(tokenKey, entityKey)
        otherShares = otherSnap.shares(tokenKey, entityKey)
        if shares != otherShares:
            return False
    return True
