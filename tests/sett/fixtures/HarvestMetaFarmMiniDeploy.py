from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config


class HarvestMetaFarmMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.harvest.renCrv.params
        want = sett_config.harvest.renCrv.params.want

        return (params, want)

    def post_deploy_setup(self, deploy=True):
        # TODO(bodu): Check if there's any post deploy setup we need to do.
        self.strategy.setWithdrawalMaxDeviationThreshold(50, {"from": self.governance})
