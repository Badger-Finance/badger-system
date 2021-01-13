from brownie import web3, DiggRewardsFaucet

from scripts.systems.digg_minimal import deploy_digg_minimal
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase


# Generic DIGG sett mini deploy logic.
class DiggSettMiniDeployBase(SettMiniDeployBase):
    def post_deploy_setup(self):
        # Track our digg system within badger system for convenience.
        self.badger.add_existing_digg(self.digg)

    def pre_deploy_setup(self):
        """
        Deploy DIGG System and Dynamic oracle for testing.
        """
        deployer = self.deployer
        devProxyAdminAddress = web3.toChecksumAddress("0x20dce41acca85e8222d6861aa6d23b6c941777bf")
        daoProxyAdminAddress = web3.toChecksumAddress("0x11a9d034b1bbfbbdcac9cb3b86ca7d5df05140f2")
        self.digg = deploy_digg_minimal(
            deployer, devProxyAdminAddress, daoProxyAdminAddress, owner=deployer
        )

        self.badger.deploy_logic("DiggRewardsFaucet", DiggRewardsFaucet)

        # Deploy dynamic oracle (used for testing ONLY).
        self.digg.deploy_dynamic_oracle()
        # Authorize dynamic oracle as a data provider to median oracle.
        self.digg.marketMedianOracle.addProvider(
            self.digg.dynamicOracle,
            {"from": deployer},
        )
        
