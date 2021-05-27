import datetime

ONE_MINUTE = 60
ONE_HOUR = 3600
ONE_DAY = 24 * ONE_HOUR
ONE_YEAR = 1 * 365 * ONE_DAY


def days(days):
    return int(days * 86400.0)


def hours(hours):
    return int(hours * 3600.0)


def minutes(minutes):
    return int(minutes * 60.0)


def to_utc_date(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def to_timestamp(date):
    print(date.timestamp())
    return int(date.timestamp())


def to_minutes(duration):
    return duration / ONE_MINUTE


def to_days(duration):
    return duration / ONE_DAY


def to_hours(duration):
    return duration / ONE_HOUR
