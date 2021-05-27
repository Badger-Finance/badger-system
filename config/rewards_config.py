from helpers.time_utils import hours


class RewardsConfig:
    def __init__(self):
        self.globalStakingStartBlock = 11252068
        self.rootUpdateMinInterval = hours(0.9)
        self.maxStartBlockAge = 3200
        self.debug = False


rewards_config = RewardsConfig()
