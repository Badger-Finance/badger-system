from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config


class YearnMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.yearn.bvyWBTC.params
        params.want = self.badger.token

        want = self.badger.token

        return (params, want)

    def post_deploy_setup(self, deploy=True):
        """
        Initialize wrapper
        """
        super().post_deploy_setup(deploy=deploy)

        if not deploy:
            return
