from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config


class UnitProtocolRenBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.unitRenBtc.params
        want = sett_config.native.unitRenBtc.params.want

        return (params, want)
