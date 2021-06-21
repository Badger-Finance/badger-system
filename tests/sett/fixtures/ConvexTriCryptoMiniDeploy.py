from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config, digg_config
from helpers.registry import registry
from helpers.token_utils import distribute_from_whales
from brownie import *
from helpers.proxy_utils import deploy_proxy
import json
from helpers.constants import AddressZero


class ConvexTriCryptoMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.convexTriCrypto.params
        want = sett_config.native.convexTriCrypto.params.want

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

        contract = StrategyConvexStakingOptimizer.deploy({"from": self.deployer})
        self.strategy = deploy_proxy(
            "StrategyConvexStakingOptimizer",
            StrategyConvexStakingOptimizer.abi,
            contract.address,
            web3.toChecksumAddress(self.badger.devProxyAdmin.address),
            contract.initialize.encode_input(
                self.governance.address,
                self.strategist.address,
                self.controller.address,
                self.keeper.address,
                self.guardian.address, 
                [params.want, self.badger.badgerTree, AddressZero, AddressZero],
                params.pid,
                [
                    params.performanceFeeGovernance,
                    params.performanceFeeStrategist,
                    params.withdrawalFee,
                ],
                (params.curvePool.swap, params.curvePool.wbtcPosition, params.curvePool.numElements)
            ),
            self.deployer,
        )

        self.badger.sett_system.strategies[self.key] = self.strategy

        assert self.controller.address == self.strategy.controller()

        self.controller.approveStrategy(self.strategy.want(), self.strategy.address, {"from": self.governance})
        self.controller.setStrategy(self.strategy.want(), self.strategy.address, {"from": self.governance})

        assert self.controller.strategies(self.vault.token()) == self.strategy.address
