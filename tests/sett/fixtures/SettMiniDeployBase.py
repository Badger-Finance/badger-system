from tests.helpers import distribute_from_whales
from scripts.systems.badger_minimal import deploy_badger_minimal


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

    def deploy(self):
        self.badger = deploy_badger_minimal(self.deployer)
        self.deploy_required_logic()

        self.pre_deploy_setup()

        (params, want) = self.fetch_params()

        distribute_from_whales(self.badger, self.deployer)

        self.controller = self.badger.add_controller(self.key)
        self.vault = self.badger.deploy_sett(
            self.key,
            want,
            self.controller,
            governance=self.governance,
            strategist=self.strategist,
            keeper=self.keeper,
        )

        self.strategy = self.badger.deploy_strategy(
            self.key,
            self.strategyName,
            self.controller,
            params,
            governance=self.governance,
            strategist=self.strategist,
            keeper=self.keeper,
            guardian=self.guardian,
        )

        self.badger.wire_up_sett(self.vault, self.strategy, self.controller)

        self.post_deploy_setup()

        return self.badger

    def deploy_required_logic(self):
        self.badger.deploy_core_logic()
        self.badger.deploy_sett_core_logic()
        self.badger.deploy_sett_strategy_logic()

    # ===== Specific instance must implement =====
    def fetch_params(self):
        return False

    def pre_deploy_setup(self):
        return False

    def post_deploy_setup(self):
        return False
