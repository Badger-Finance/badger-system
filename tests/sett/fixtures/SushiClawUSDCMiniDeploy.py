from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import sett_config, claw_config
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.claw_system import connect_claw
from scripts.systems.claw_minimal import deploy_claw_minimal
from helpers.registry import registry


class SushiClawUSDCMiniDeploy(SettMiniDeployBase):
    def __init__(
        self,
        key,
        strategyName,
        deployer,
        empName,
        strategist=None,
        governance=None,
        keeper=None,
        guardian=None,
    ):
        super().__init__(
            key,
            strategyName,
            deployer,
            strategist=strategist,
            governance=governance,
            keeper=keeper,
            guardian=guardian,
        )
        # Set the emp synthetic name so we know which token to use.
        self.empName = empName

    def pre_deploy_setup(self, deploy=True):
        """
        Deploy CLAW System and Dynamic oracle for testing.
        """
        # TODO: Once deployed, we can connect to the configured CLAW
        # system to perform tests, but for now do ignore the deploy flag.
        # since we want to connect to the existing badger system for tests.
        # if not deploy:
        #     claw = connect_claw(claw_config.prod_json)
        #     self.claw = claw
        #     return

        deployer = self.deployer
        self.claw = deploy_claw_minimal(deployer)
        self.claw.set_emp(self.empName)

    def fetch_params(self):
        params = sett_config.sushi.sushiClawUSDC.params

        sushiswap = SushiswapSystem()
        token = self.claw.emp.tokenCurrency()
        if sushiswap.hasPair(token, registry.tokens.usdc):
            params.want = sushiswap.getPair(token, registry.tokens.usdc)
        else:
            params.want = sushiswap.createPair(
                token,
                registry.tokens.usdc,
                self.deployer,
            )
        want = params.want
        params.badgerTree = self.badger.badgerTree

        return (params, want)

    def post_deploy_setup(self, deploy=True):
        """
        Add claw system to badger system.
        """
        self.badger.add_existing_claw(self.claw)

    def post_vault_deploy_setup(self, deploy=True):
        """
        Create lp pool if not exists.
        """
        if not deploy:
            return

        # Setup sushi reward allocations.
        sushiswap = SushiswapSystem()
        pid = sushiswap.add_chef_rewards(self.want)

        # Pass in LP token pool id to underlying strategy.
        self.params.pid = pid
