from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from helpers.token_utils import distribute_test_ether, distribute_from_whales
from config.badger_config import badger_config, sett_config
from scripts.systems.mstable_system import MStableSystem
from helpers.constants import AddressZero
from helpers.registry import registry
from brownie import MStableVoterProxy, Wei, accounts
from dotmap import DotMap
from scripts.systems.constants import SettType


class MStableImBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.imBtc.params
        want = sett_config.native.imBtc.params.want

        params.badgerTree = self.badger.badgerTree

        return (params, want)

    def pre_deploy_setup(self, deploy=True):
        """
        Deploy MStableVoterProxy
        """

        self.dualGovernance = accounts[6]
            
        mstable_config_test = DotMap(
            dualGovernance=self.dualGovernance, # Placeholder as dualGovernance multi-sig hasn't been launched
            badgerGovernance=self.governance,
            strategist=self.strategist,
            keeper=self.keeper,
            configAddress1=registry.mstable.nexus,
            configAddress2=registry.mstable.votingLockup,
            rates=8000, # Placeholder: redistributionRate set to 80%
        )

        self.mstable = MStableSystem(self.deployer, self.badger.devProxyAdmin, mstable_config_test)
        self.mstable.deploy_logic("MStableVoterProxy", MStableVoterProxy)
        self.mstable.deploy_voterproxy()

        # required to pass proxy address to strategy upon deployment
        self.badger.mstable = self.mstable

    def post_deploy_setup(self, deploy=True):
        """
        Add strategy to MStableVoterProxy
        """

        # Deploy strategy and vault on simulation test
        if not deploy:
            distribute_test_ether(self.deployer, Wei("20 ether"))

            (params, want) = self.fetch_params()

            self.params = params
            self.want = want

            self.controller = self.badger.add_controller(self.key)
            self.vault = self.badger.deploy_sett(
                self.key,
                self.want,
                self.controller,
                governance=self.governance,
                strategist=self.strategist,
                keeper=self.keeper,
                guardian=self.guardian,
                sett_type=SettType.DEFAULT,
            )
            print("Deploying Strategy with key: ", self.key)
            self.strategy = self.badger.deploy_strategy(
                self.key,
                self.strategyName,
                self.controller,
                self.params,
                governance=self.governance,
                strategist=self.strategist,
                keeper=self.keeper,
                guardian=self.guardian,
            )

            self.badger.wire_up_sett(self.vault, self.strategy, self.controller)

        # Add strat to voterproxy
        self.mstable.voterproxy.supportStrategy(
            self.strategy.address, 
            registry.mstable.pools.imBtc.vault,
            {'from': self.dualGovernance}
        ) # Must be dualGovernance

        # Add final state of mstable system to badger system
        self.badger.mstable = self.mstable

        # Distribute tokens from whales to deployer (including fPmBtcHBtc, imbtc & mta)
        distribute_from_whales(self.deployer, 1)
