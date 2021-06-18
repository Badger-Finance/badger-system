from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import sett_config
from helpers.token_utils import distribute_from_whales
from brownie import *
from helpers.proxy_utils import deploy_proxy


class HelperCvxMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.helper.cvx.params
        want = sett_config.helper.cvx.params.want

        return (params, want)

    def post_vault_deploy_setup(self, deploy=True):
        if not deploy:
            return
        distribute_from_whales(self.deployer, 1)
