from dotmap import DotMap
from assistant.rewards.config import config
# Gather all relevant events from rewards contacts
from assistant.rewards.calc_distributions import calc_geyser_distributions
from assistant.rewards.calc_stakes import calc_geyser_stakes

def main(badger, startBlock, endBlock):
    merkle_allocations = DotMap()

    for geyser in badger.geysers:
    # Determine how many tokens of each time should be distributed during this time / block interval using unlockSchedules
        distributions = calc_geyser_distributions(geyser.contract, startBlock, endBlock)
        stakeWeights = calc_geyser_stakes(geyser.contract, config.globalStartBlock, startBlock, endBlock)
        allocations = calc_token_allocations(distributions, stakeWeights)

        # Confirm that totals don't exceed the expected - one safeguard against expensive invalid roots on the non-contract side