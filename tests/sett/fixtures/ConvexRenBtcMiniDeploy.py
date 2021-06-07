from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config
from helpers.registry import registry
from helpers.token_utils import distribute_from_whales


class ConvexRenBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.convexRenCrv.params
        want = sett_config.native.convexRenCrv.params.want

        params.badgerTree = self.badger.badgerTree

        return (params, want)

    def post_vault_deploy_setup(self, deploy=True):
        distribute_from_whales(self.deployer, 1)
