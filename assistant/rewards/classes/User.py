from rich.console import Console

console = Console()


class User:
    def __init__(
        self,
        address,
        currentDeposited,
        lastUpdated,
    ):
        self.address = address
        self.currentDeposited = currentDeposited
        self.lastUpdated = lastUpdated
        self.shareSeconds = 0

    def __repr__(self):
        return "User({},{},{},{})".format(
            self.address,
            self.currentDeposited,
            self.lastUpdated,
            self.shareSeconds,
        )

    def process_transfer(self, transfer):
        transfer_timestamp = int(transfer["transaction"]["timestamp"])
        transfer_amount = transfer["amount"]

        secondsSinceLastAction = transfer_timestamp - self.lastUpdated
        assert secondsSinceLastAction >= 0
        self.lastUpdated = transfer_timestamp
        self.shareSeconds += secondsSinceLastAction * self.currentDeposited
        self.currentDeposited += transfer_amount
        if self.currentDeposited < 0:
            self.currentDeposited = 0
