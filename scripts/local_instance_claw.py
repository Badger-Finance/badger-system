import time
import decouple
from brownie import accounts, Wei
from rich.console import Console

from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.badger_system import print_to_file
from scripts.systems.claw_minimal import deploy_claw_minimal
from scripts.systems.badger_system import connect_badger
from helpers.registry import token_registry
from helpers.time_utils import days
from helpers.token_utils import (
    distribute_from_whales,
    distribute_test_ether,
)
from config.badger_config import (
    sett_config,
)

console = Console()


def main():
    """
    Connect to badger, distribute assets to specified test user, and keep ganache open.
    Ganache will run with your default brownie settings for mainnet-fork
    """

    # The address to test with

    # badger = connect_badger("deploy-final.json", load_deployer=False, load_keeper=False, load_guardian=False)

    # TODO: After prod deployment, just connect instead.
    deploy_claw_minimal(accounts[0], printToFile=True)
    # Deploy claw setts
    # sushiswap = SushiswapSystem()
    # for (settId, empName) in [("native.sushiBClawUSDC",  "bClaw"), ("native.sushiSClawUSDC", "sClaw")]:
    #     params = sett_config.sushi.sushiClawUSDC.params
    #     token = claw.emps[empName].tokenCurrency()
    #     if sushiswap.hasPair(token, token_registry.wbtc):
    #         params.want = sushiswap.getPair(token, token_registry.wbtc)
    #     else:
    #         params.want = sushiswap.createPair(
    #             token,
    #             token_registry.wbtc,
    #             badger.deployer,
    #         )
    #     want = params.want
    #     params.badgerTree = badger.badgerTree
    #     params.pid = sushiswap.add_chef_rewards(want)

    #     strategist = badger.daoProxyAdmin
    #     controller = badger.add_controller(settId)
    #     badger.deploy_sett(
    #         settId,
    #         want,
    #         controller,
    #         governance=badger.daoProxyAdmin,
    #         strategist=strategist,
    #         keeper=badger.keeper,
    #         guardian=badger.guardian,
    #     )
    #     badger.deploy_strategy(
    #         settId,
    #         "StrategySushiLpOptimizer",
    #         controller,
    #         params,
    #         governance=badger.daoProxyAdmin,
    #         strategist=strategist,
    #         keeper=badger.keeper,
    #         guardian=badger.guardian,
    #     )

    # print_to_file(badger, "deploy-test.json")

    console.print("[green]=== ✅ Test ENV Setup Complete ✅ ===[/green]")
    # Keep ganache open until closed
    time.sleep(days(365))
