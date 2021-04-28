from dataclasses import dataclass  
from helpers.time_utils import days, to_days, to_hours, to_utc_date

@dataclass
class Schedule:
    initialTokensLocked: int
    endTime: int
    duration: int
    startTime: int

    def __repr__(self):
        return "Schedule(initalTokensLocked={},endTime={},duration={} days,startTime={}".format(
            self.initialTokensLocked,
            to_utc_date(self.endTime),
            to_days(self.duration),
            to_utc_date(self.startTime)
        )


