from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config
from helpers.registry import registry
from helpers.token_utils import distribute_from_whales
from brownie import *
from helpers.proxy_utils import deploy_proxy


class ConvexRenBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.convexRenCrv.params
        want = sett_config.native.convexRenCrv.params.want

        params.badgerTree = self.badger.badgerTree

        return (params, want)

    def post_vault_deploy_setup(self, deploy=True):
        if not deploy:
            return
        distribute_from_whales(self.deployer, 1)

    def post_deploy_setup(self, deploy):
        if deploy:
            return

        (params, want) = self.fetch_params()

        self.controller = interface.IController(self.vault.controller())

        timelock = accounts.at("0x21CF9b77F88Adf8F8C98d7E33Fe601DC57bC0893", force=True)


        contract = StrategyConvexLpOptimizer.deploy({"from": self.deployer})
        self.strategy = deploy_proxy(
            "StrategyConvexLpOptimizer",
            StrategyConvexLpOptimizer.abi,
            contract.address,
            web3.toChecksumAddress(self.badger.devProxyAdmin.address),
            contract.initialize.encode_input(
                self.governance.address,
                self.strategist.address,
                self.controller.address,
                self.keeper.address,
                self.guardian.address, 
                [params.want, self.badger.badgerTree,],
                params.pid,
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
            ),
            self.deployer,
        )

        self.badger.sett_system.strategies[self.key] = self.strategy

        #self.badger.wire_up_sett(self.vault, self.strategy, self.controller)
        self.controller.approveStrategy(self.strategy.want(), self.strategy.address, {"from": timelock})
        self.controller.setStrategy(self.strategy.want(), self.strategy.address, {"from": timelock})

        assert self.controller.strategies(self.vault.token()) == self.strategy.address
        

