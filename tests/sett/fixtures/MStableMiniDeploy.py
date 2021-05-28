from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config
from systems.mstable_system import MStableSystem
from helpers.constants import AddressZero
from helpers.registry import mstable_registry
from brownie import MStableVoterProxy


class MStableMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.imBtc.params
        want = sett_config.native.imBtc.params.want

        return (params, want)

    def pre_deploy_setup(self, deploy=True):
        """
        Deploy MStableVoterProxy
        """
        mstable_config_test = DotMap(
            dualGovernance=AddressZero, # Placeholder as dualGovernance multi-sig hasn't been launched
            badgerGovernance=self.governance,
            strategist=self.strategist,
            keeper=self.keeper,
            configAddress1=mstable_registry.nexus,
            configAddress2=mstable_registry.votingLockup,
            rates=500, # Placeholder: redistributionRate set to 50%
        )

        mstable = MStableSystem(self.deployer, self.badger.devProxyAdmin, mstable_config_test)
        mstable.deploy_logic("MStableVoterProxy", MStableVoterProxy)
        mstable.deploy_voterproxy_proxy()

    def post_deploy_setup(self, deploy=True):
