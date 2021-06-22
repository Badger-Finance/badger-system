from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import sett_config
from helpers.token_utils import distribute_from_whales
from brownie import *
from helpers.proxy_utils import deploy_proxy
from scripts.systems.constants import SettType


class HelperCvxCrvMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.helper.cvxCrv.params
        want = sett_config.helper.cvxCrv.params.want

        return (params, want)

    def post_vault_deploy_setup(self, deploy=True):
        if deploy:
            distribute_from_whales(self.deployer, 1)

    def post_deploy_setup(self, deploy):
        if deploy:
            return

        (params, want) = self.fetch_params()

        self.controller = interface.IController(self.vault.controller())

        # Deploy strategy
        contract = StrategyCvxCrvHelper.deploy({"from": self.deployer})
        self.strategy = deploy_proxy(
            "StrategyCvxCrvHelper",
            StrategyCvxCrvHelper.abi,
            contract.address,
            web3.toChecksumAddress(self.badger.devProxyAdmin.address),
            contract.initialize.encode_input(
                self.governance.address,
                self.strategist.address,
                self.controller.address,
                self.keeper.address,
                self.guardian.address, 
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
            ),
            self.deployer,
        )

        self.badger.sett_system.strategies[self.key] = self.strategy

        # Vault uses testMultisig
        self.testMultisig = accounts.at(self.vault.governance(), force=True)

        # NB: Not all vaults are pauseable.
        try:
            if self.vault.paused():
                self.vault.unpause({"from": self.testMultisig})
        except exceptions.VirtualMachineError:
            pass

        # Check that vault's and Strat's controller is the same
        assert self.vault.controller() == self.strategy.controller()

        # Check that want is the same for vault and strategy
        assert self.vault.token() == self.strategy.want()

        # Add strategy to controller for want
        self.controller.approveStrategy(self.strategy.want(), self.strategy.address, {"from": self.governance})
        self.controller.setStrategy(self.strategy.want(), self.strategy.address, {"from": self.governance})

        assert self.controller.strategies(self.vault.token()) == self.strategy.address
        assert self.controller.vaults(self.strategy.want()) == self.vault.address

    # def post_deploy_setup(self, deploy):
    #     # Deploy during simulation while contracts get deployed:
    #     if deploy:
    #         return

    #     (params, want) = self.fetch_params()

    #     self.controller = interface.IController(self.vault.controller())

    #     contract = StrategyCvxCrvHelper.deploy({"from": self.deployer})
    #     self.strategy = deploy_proxy(
    #         "StrategyCvxCrvHelper",
    #         StrategyCvxCrvHelper.abi,
    #         contract.address,
    #         web3.toChecksumAddress(self.badger.devProxyAdmin.address),
    #         contract.initialize.encode_input(
    #             self.governance.address,
    #             self.strategist.address,
    #             self.controller.address,
    #             self.keeper.address,
    #             self.guardian.address, 
    #             [
    #                 params.performanceFeeGovernance,
    #                 params.performanceFeeStrategist,
    #                 params.withdrawalFee,
    #             ],
    #         ),
    #         self.deployer,
    #     )

    #     self.badger.sett_system.strategies[self.key] = self.strategy

    #     assert self.controller.address == self.strategy.controller()

    #     timelock = accounts.at("0x21CF9b77F88Adf8F8C98d7E33Fe601DC57bC0893", force=True)

    #     self.controller.approveStrategy(self.strategy.want(), self.strategy.address, {"from": timelock})
    #     self.controller.setStrategy(self.strategy.want(), self.strategy.address, {"from": timelock})

    #     # Add vault to controller for want
    #     self.controller.setVault(self.vault.token(), self.vault.address, {"from": timelock})

    #     assert self.controller.strategies(self.vault.token()) == self.strategy.address
