from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import sett_config

class KeeperRenbtcLpOptimizerMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.keeper.keeperRenbtc.params
        params.badgerRewardsManager = self.badger.badgerRewardsManager

        want = params.want

        return (params, want)
