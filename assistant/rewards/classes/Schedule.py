from dataclasses import dataclass  

@dataclass
class Schedule:
    initialTokensLocked: int
    endTime: int
    duration: int
    startTime: int


