from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config


class CurveGaugeTBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.tbtcCrv.params
        want = sett_config.native.tbtcCrv.params.want

        return (params, want)
