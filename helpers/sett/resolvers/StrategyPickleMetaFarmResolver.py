"""
Extra to track
    if name == "StrategyPickleMetaFarm":
        pickle = interface.IERC20(strategy.pickle())
        pickleJar = interface.IPickleJar(strategy.pickleJar())
        pickleChef = interface.IPickleChef(strategy.pickleChef())
        stakingRewards = interface.IStakingRewards(strategy.pickleStaking())

        result.strategy.pickleBalance = pickle.balanceOf(strategy)
        result.strategy.pickleJar.stakedShares = pickleJar.balanceOf(strategy)
        result.strategy.pickleChef.stakedShares = pickleChef.userInfo(
            strategy.pid(), strategy
        )[0]
        result.strategy.stakingRewards.stakedPickle = stakingRewards.balanceOf(strategy)
        result.strategy.stakingRewards.earnedWeth = stakingRewards.earned(strategy)
        
"""


def confirm_harvest_pickle(before, after):
    """
    Harvest Should;
    - Increase the balanceOf() underlying asset in the Strategy
    - Reduce the amount of idle PICKLE to zero
    - Reduce PICKLE in pickleStaking to zero
    - Increase the ppfs on sett
    """
    assert after.strategy.balanceOf > before.strategy.balanceOf
    assert after.strategy.pickleBalance == 0
    assert after.strategy.stakingRewards.stakedPickle == 0
    if before.sett.pricePerFullShare:
        assert after.sett.pricePerFullShare > before.sett.pricePerFullShare


def confirm_migrate_pickle(before, after):
    """
    - Send all Pickle to rewards
    - Send all Weth to rewards
    - Leave no Pickle in Strategy or staking contracts
    - Leave no Weth in Strategy or staking contracts
    """
    assert False
