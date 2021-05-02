class Deployer:
    """
    Wrappers around deploys that verify properties post-deploy
    - Ensure all params result in expected variables
    - Expect all constants are as expected
    - Ensure proxies are initialized (if applicable)
    """

    def deploySmartVesting(self, params):
        return False

    def deploySmartTimelock(self, params):
        return False

    def deployRewardsEscrow(self, params):
        return False

    def deployBadgerGeyser(self, params):
        return False

    def deployBadgerTree(self, params):
        return False

    def deployBadgerHunt(self, params):
        return False

    def deploySimpleTimelock(self, params):
        return False

    def deployController(self, params):
        return False

    def deploySett(self, params):
        return False

    def deployStakingRewards(self, params):
        return False

    def deployStrategyBadgerRewards(self, params):
        return False

    def deployStrategyBadgerLpMetaFarm(self, params):
        return False

    def deployStrategyHarvestMetaFarm(self, params):
        return False

    def deployStrategyPickleMetaFarm(self, params):
        return False

    def deployStrategyCurveGaugeTbtcCrv(self, params):
        return False

    def deployStrategyCurveGaugeSbtcCrv(self, params):
        return False

    def deployStrategyCurveGaugeRenBtcCrv(self, params):
        return False

    def deployHoneypotMeme(self, params):
        return False
