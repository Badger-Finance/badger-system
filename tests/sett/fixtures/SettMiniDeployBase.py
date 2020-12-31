from helpers.token_utils import distribute_from_whales, distribute_test_ether
from scripts.systems.badger_minimal import deploy_badger_minimal
from brownie import *


class SettMiniDeployBase:
    def __init__(
        self,
        key,
        strategyName,
        deployer,
        strategist=None,
        governance=None,
        keeper=None,
        guardian=None,
    ):
        self.key = key
        self.strategyName = strategyName

        if not strategist:
            strategist = deployer
        if not governance:
            governance = deployer
        if not keeper:
            keeper = deployer
        if not guardian:
            guardian = deployer

        self.strategist = strategist
        self.governance = governance
        self.keeper = keeper
        self.guardian = guardian
        self.deployer = deployer

    def deploy(self, new_badger=True):
        if (new_badger):
            self.badger = deploy_badger_minimal(self.deployer, self.keeper, self.guardian)
            self.controller = self.badger.add_controller(self.key)
        else:
            self.badger=""
        self.deploy_required_logic()

        self.pre_deploy_setup()

        (params, want) = self.fetch_params()

        self.params = params
        self.want = want

        distribute_test_ether(self.deployer, Wei("20 ether"))
        distribute_from_whales(self.deployer)

        self.controller = self.badger.add_controller(self.key)
        self.vault = self.badger.deploy_sett(
            self.key,
            self.want,
            self.controller,
            governance=self.governance,
            strategist=self.strategist,
            keeper=self.keeper,
            guardian=self.guardian,
        )

        self.post_vault_deploy_setup()

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

        self.post_deploy_setup()

        assert self.vault.paused()

        self.vault.unpause({"from": self.governance})

        return self.badger

    def deploy_required_logic(self):
        self.badger.deploy_core_logic()
        self.badger.deploy_sett_core_logic()
        self.badger.deploy_sett_strategy_logic_for(self.strategyName)

    # ===== Specific instance must implement =====
    def fetch_params(self):
        return False

    def pre_deploy_setup(self):
        return False

    def post_deploy_setup(self):
        return False

    def post_vault_deploy_setup(self):
        return False
