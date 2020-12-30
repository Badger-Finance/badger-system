class User:
    def __init__(self, address, currentDeposited, lastUpdated):
        self.address = address
        self.currentDeposited = currentDeposited
        self.lastUpdated = lastUpdated
        self.shareSeconds = 0

    def __repr__(self):
        return "User({},{},{},{})".format(
            self.address,
            self.currentDeposited / 10 ** 18,
            self.lastUpdated,
            self.shareSeconds,
        )
