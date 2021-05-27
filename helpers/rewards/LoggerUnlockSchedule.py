class LoggerUnlockSchedule:
    def __init__(self, raw_schedule):
        """
        The unlock schedule is returned from the contract in the following format:
        (amount, end, duration, start)
        """
        self.beneficiary = raw_schedule[0]
        self.token = raw_schedule[1]
        self.amount = raw_schedule[2]
        self.start = raw_schedule[3]
        self.end = raw_schedule[4]
        self.duration = raw_schedule[5]
