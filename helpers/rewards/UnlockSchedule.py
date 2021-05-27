class UnlockSchedule:
    def __init__(self, token, raw_schedule):
        """
        The unlock schedule is returned from the contract in the following format:
        (amount, end, duration, start)
        """
        self.token = token
        self.amount = raw_schedule[0]
        self.end = raw_schedule[1]
        self.duration = raw_schedule[2]
        self.start = raw_schedule[3]
