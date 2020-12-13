from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config


class CurveGaugeRenBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.renCrv.params
        want = sett_config.native.renCrv.params.want

        return (params, want)
