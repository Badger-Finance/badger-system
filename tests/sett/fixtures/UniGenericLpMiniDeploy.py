from scripts.systems.uniswap_system import UniswapSystem
from config.badger_config import sett_config
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase


class UniGenericLpMiniDeploy(SettMiniDeployBase):
    def __init__(
        self,
        key,
        strategyName,
        deployer,
        tokens,  # lp token pair
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
        # Set lp token pair.
        self.tokens = tokens

    def fetch_params(self):
        params = sett_config.uni.uniGenericLp.params

        uniswap = UniswapSystem()
        want = uniswap.getPair(*self.tokens)

        params.want = want

        return (params, want)
