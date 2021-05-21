from helpers.constants import APPROVED_STAKER_ROLE
from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.sushiswap_system import SushiswapSystem
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config
from helpers.registry import registry


class SushiBadgerLpOptimizerMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.sushi.sushiWethWBtc.params

        sushiswap = SushiswapSystem()
        want = sushiswap.getPair(registry.tokens.weth, registry.tokens.wbtc)

        assert want == "0xCEfF51756c56CeFFCA006cD410B03FFC46dd3a58"

        params.want = want
        params.badgerTree = self.badger.badgerTree
        params.pid = registry.sushiswap.pids.sushiEthWBtc

        return (params, want)
