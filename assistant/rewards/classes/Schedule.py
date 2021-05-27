from dataclasses import dataclass
from helpers.time_utils import days, to_days, to_hours, to_utc_date


@dataclass
class Schedule:
    sett: str
    token: str
    initialTokensLocked: int
    startTime: int
    endTime: int
    duration: int

    def __repr__(self):
        return "Schedule(sett={},token={},initalTokensLocked={},startTime={},duration={} days,endTime={}".format(
            self.sett,
            self.token,
            self.initialTokensLocked,
            to_utc_date(self.startTime),
            to_days(self.duration),
            to_utc_date(self.endTime),
        )
