from scripts.systems.pancakeswap_system import PancakeswapSystem
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase


class PancakeMiniDeploy(SettMiniDeployBase):
    def __init__(
        self,
        key,
        strategyName,
        deployer,
        params,
        tokens,
        # Want is used for optional validation (we always fetch pool lp token).
        want=None,
        # Pid is used for optional validation (we always fetch pool id).
        pid=None,
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
        self.params = params
        self.tokens = tokens
        if len(self.tokens) != 2:
            raise Exception("expected 2 tokens as lp token pair")
        self.want = want
        self.pid = pid

    def fetch_params(self):
        """
        Create liquidity pool if not exists and setup reward allocations.
        """
        params = self.params

        pancakeswap = PancakeswapSystem()
        if pancakeswap.hasPair(*self.tokens):
            params.want = pancakeswap.getPair(*self.tokens)
        else:
            params.want = pancakeswap.createPair(*(self.tokens + [self.deployer]))

        want = params.want
        if self.want is not None:
            assert self.want == want

        # Setup reward allocations if not already exists.
        # This either adds or sets the current CAKE allocation
        # for the lp token pool to be an average amount of allocation points.
        pancakeswap = PancakeswapSystem()
        pid = pancakeswap.add_chef_rewards(self.want)

        if self.pid is not None:
            assert self.pid == pid

        self.params.pid = pid

        params.want = want
        params.token0 = self.tokens[0]
        params.token1 = self.tokens[1]

        return (params, want)
