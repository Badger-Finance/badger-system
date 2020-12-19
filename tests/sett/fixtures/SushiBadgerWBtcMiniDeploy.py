from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config

class SushiBadgerWBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.sushi.sushiBadgerWBtc.params
        want = sett_config.sushi.sushiBadgerWBtc.params.want

        return (params, want)

    def post_deploy_setup(self):
        assert False
