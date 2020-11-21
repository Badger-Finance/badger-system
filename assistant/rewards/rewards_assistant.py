from dotmap import DotMap
from assistant.rewards.config import config

# Gather all relevant events from rewards contacts
from assistant.rewards.calc_distributions import (
    add_allocations,
    calc_geyser_distributions,
)
from assistant.rewards.calc_stakes import calc_geyser_stakes

def run(badger, startBlock, endBlock):
    main(badger, startBlock, endBlock)

def main(badger, startBlock, endBlock):
    merkle_allocations = DotMap()

    # Determine how many tokens of each type should be distributed during this time / block interval using unlockSchedules from all

    pools = [
        badger.pools.sett.native.renCrv,
        badger.pools.sett.native.sbtcCrv,
        badger.pools.sett.native.tbtcCrv,
        badger.pools.sett.pickle.renCrv,
        badger.pools.sett.harvest.renCrv,
    ]

    for geyser in pools:
        distributions = calc_geyser_distributions(geyser, startBlock, endBlock)
        stakeWeights = calc_geyser_stakes(
            geyser, config.globalStartBlock, startBlock, endBlock
        )
        allocations = add_allocations(distributions, stakeWeights)

        # Confirm that totals don't exceed the expected - one safeguard against expensive invalid roots on the non-contract side
