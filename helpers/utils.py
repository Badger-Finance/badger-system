# Assert approximate integer
def approx(actual, expected, percentage_threshold, message="approx check"):
    print(actual, expected, percentage_threshold)
    diff = int(abs(actual - expected))
    assert diff < (actual * percentage_threshold // 100), message
