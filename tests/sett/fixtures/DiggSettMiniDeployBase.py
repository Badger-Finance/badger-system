from brownie import chain, web3, DiggRewardsFaucet

from scripts.systems.digg_system import connect_digg
from scripts.systems.digg_minimal import deploy_digg_minimal
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import digg_config


# Generic DIGG sett mini deploy logic.
class DiggSettMiniDeployBase(SettMiniDeployBase):
    def post_deploy_setup(self):
        # Track our digg system within badger system for convenience.
        self.badger.add_existing_digg(self.digg)

    def pre_deploy_setup(self, deploy=True):
        """
        Deploy DIGG System and Dynamic oracle for testing.
        """
        if not deploy:
            digg = connect_digg(digg_config.prod_json)
            self.digg = digg
            self._deploy_dynamic_oracle()

            digg.constantOracle.updateAndPush({"from": digg.owner})
            # Sleep long enough that the report is valid.
            chain.sleep(digg_config.cpiOracleParams.reportDelaySec)

            # TODO: Can remove the following once core digg contracts
            # are wired up.
            # Setup frag policy & frag (required for ALL deploys).
            digg.uFragmentsPolicy.setCpiOracle(
                digg.cpiMedianOracle,
                {"from": digg.owner},
            )
            digg.uFragmentsPolicy.setMarketOracle(
                digg.marketMedianOracle,
                {"from": digg.owner},
            )
            digg.uFragmentsPolicy.setOrchestrator(
                digg.orchestrator,
                {"from": digg.owner},
            )
            digg.uFragments.setMonetaryPolicy(
                digg.uFragmentsPolicy,
                {"from": digg.owner},
            )
            return

        deployer = self.deployer
        devProxyAdminAddress = web3.toChecksumAddress("0x20dce41acca85e8222d6861aa6d23b6c941777bf")
        daoProxyAdminAddress = web3.toChecksumAddress("0x11a9d034b1bbfbbdcac9cb3b86ca7d5df05140f2")
        self.digg = deploy_digg_minimal(
            deployer, devProxyAdminAddress, daoProxyAdminAddress, owner=deployer
        )

        self.badger.deploy_logic("DiggRewardsFaucet", DiggRewardsFaucet)

        self._deploy_dynamic_oracle()

    def _deploy_dynamic_oracle(self):
        # Deploy dynamic oracle (used for testing ONLY).
        self.digg.deploy_dynamic_oracle()
        # Authorize dynamic oracle as a data provider to median oracle.
        self.digg.marketMedianOracle.addProvider(
            self.digg.dynamicOracle,
            {"from": self.deployer},
        )

