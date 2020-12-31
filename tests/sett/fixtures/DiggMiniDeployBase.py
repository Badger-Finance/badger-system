from helpers.token_utils import distribute_from_whales, distribute_test_ether
from scripts.systems.badger_minimal import deploy_badger_minimal
from brownie import *


class DiggMiniDeployBase:
    def __init__(
        self,
        strategyName,
        deployer,
        strategist=None,
        governance=None,
        keeper=None,
        guardian=None,
    ):
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

    def deploy_required_logic(self):

    # ===== Specific instance must implement =====
    def fetch_params(self):
        return False

    def pre_deploy_setup(self):
        return False

    def post_deploy_setup(self):
        return False

    def post_vault_deploy_setup(self):
        return False
