from brownie import Wei
from helpers.network import network_manager
from helpers.time_utils import days, hours, minutes

# Setts that are not tendable will automatically be skipped
# Lines can be commented out here to skip Setts

setts_to_skip = {
    "eth": {
        "harvest": [
            "native.uniBadgerWbtc",
            "native.badger",
            "native.sushiBadgerWbtc",
            "native.digg",
            "native.uniDiggWbtc",
            "native.sushiDiggWbtc",
        ],
        "tend": [],
        "earn": [
            "native.uniBadgerWbtc",
            "native.badger",
            "native.sushiBadgerWbtc",
            "native.digg",
            "native.uniDiggWbtc",
            "native.sushiDiggWbtc",
        ],
    },
    "bsc": {
        "harvest": ["native.pancakeBnbBtcB", "native.pancakeBnbBtcb", "native.test"],
        "tend": [],
        "earn": [],
    },
}

run_intervals = {
    "eth": {
        "harvest": days(1),
        "tend": hours(12),
        "earn": minutes(10),
    },
    "bsc": {
        "harvest": minutes(10),
        "tend": minutes(15),
        "earn": minutes(10),
    },
}

earn_default_percentage_threshold = 0.01
btc_threshold = Wei("3 ether")

earn_threshold_value_override = {
    "eth": {
        "native.renCrv": btc_threshold,
        "native.sbtcCrv": btc_threshold,
        "native.tbtcCrv": btc_threshold,
        "harvest.renCrv": btc_threshold,
        "native.sushiWbtcEth": Wei("0.00000202 ether"),
    },
    "bsc": {"native.pancakeBnbBtcb": Wei("0.0001 ether")},
}


class KeeperConfig:
    def __init__(self):
        self.debug = False
        self.setts_to_skip = {}
        self.run_intervals = run_intervals
        self.earn_default_percentage_threshold = earn_default_percentage_threshold
        self.earn_threshold_value_override = earn_threshold_value_override

    def has_earn_threshold_override_active_chain(self, key):
        chain = network_manager.get_active_network()
        override = self.get_earn_threshold_override(chain, key)
        if override == 0:
            return False
        else:
            return True

    def get_earn_threshold_override(self, chain, key):
        if key in self.earn_threshold_value_override[chain].keys():
            return self.earn_threshold_value_override[chain][key]
        else:
            return 0

    def get_active_chain_earn_threshold_override(self, key):
        chain = network_manager.get_active_network()
        return self.get_earn_threshold_override(chain, key)

    def get_run_interval(self, chain, action):
        if chain in self.setts_to_skip.keys():
            return self.run_intervals[chain][action]
        else:
            raise Exception("Run interval not found for {}".format(chain))

    def get_skipped_setts(self, chain, action):
        if chain in self.setts_to_skip.keys():
            return self.setts_to_skip[chain][action]
        else:
            raise Exception("Setts not found for {}".format(chain))

    def add_skipped_setts(self, setts_to_skip):
        self.setts_to_skip = setts_to_skip

    def get_active_chain_skipped_setts(self, action):
        chain = network_manager.get_active_network()
        return self.get_skipped_setts(chain, action)

    def get_active_chain_run_interval(self, action):
        chain = network_manager.get_active_network()
        return self.get_run_interval(chain, action)


keeper_config = KeeperConfig()
keeper_config.add_skipped_setts(setts_to_skip)
