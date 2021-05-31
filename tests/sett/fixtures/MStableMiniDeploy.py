from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config
from scripts.systems.mstable_system import MStableSystem
from helpers.constants import AddressZero
from helpers.registry import registries
from brownie import MStableVoterProxy
from dotmap import DotMap


class MStableMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.imBtc.params
        want = sett_config.native.imBtc.params.want

        return (params, want)

    def pre_deploy_setup(self, deploy=True):
        """
        Deploy MStableVoterProxy
        """
        registry = registries.get_registry("eth")
            
        mstable_config_test = DotMap(
            dualGovernance=self.governance, # Placeholder as dualGovernance multi-sig hasn't been launched
            badgerGovernance=self.governance,
            strategist=self.strategist,
            keeper=self.keeper,
            configAddress1=registry.mstable.nexus,
            configAddress2=registry.mstable.votingLockup,
            rates=500, # Placeholder: redistributionRate set to 50% (To confirm reasonable amount with alsco77)
        )

        self.mstable = MStableSystem(self.deployer, self.badger.devProxyAdmin, mstable_config_test)
        self.mstable.deploy_logic("MStableVoterProxy", MStableVoterProxy)
        self.mstable.deploy_voterproxy_proxy()

        self.badger.mstable = self.mstable

    def post_deploy_setup(self, deploy=True):
        """
        Add strategy to MStableVoterProxy
        """
        self.mstable.voterproxy.supportStrategy(self.strategy.address, self.vault.address, {'from': self.governance}) # Must be dualGovernance
