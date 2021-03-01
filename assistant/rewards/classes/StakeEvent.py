class StakeEvent:
    def __init__(self, rawEvent):
        self.user = rawEvent["user"]
        self.amount = rawEvent["amount"]
        self.total = rawEvent["total"]
        self.timestamp = rawEvent["timestamp"]
        self.blockNumber = rawEvent["blockNumber"]
        self.data = rawEvent["data"]
