# Assert approximate integer
def approx(actual, expected, percentage_threshold):
    print(actual, expected, percentage_threshold)
    diff = int(abs(actual - expected))
    return diff < (actual * percentage_threshold // 100)


def Eth(value):
    return value / 1e18


def val(amount):
    return "{:,.2f}".format(amount / 1e18)


def sec(amount):
    return "{:,.1f}".format(amount / 1e12)

