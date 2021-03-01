from assistant.rewards.rewards_utils import publish_new_root
from helpers.proxy_utils import deploy_proxy
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
import os
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.badger_system import print_to_file
from scripts.systems.digg_system import connect_digg
from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.claw_minimal import deploy_claw_minimal
import time

from brownie import *
import decouple
from config.badger_config import (
    badger_config,
    sett_config,
    digg_config,
    claw_config
)
from helpers.constants import *
from helpers.time_utils import days
from helpers.token_utils import (
    distribute_from_whales,
    distribute_meme_nfts,
    distribute_test_ether,
)
from rich.console import Console
from scripts.deploy.deploy_digg import (
    deploy_digg_with_existing_badger,
    digg_deploy_flow,
)
from scripts.systems.badger_system import connect_badger
from helpers.registry import token_registry
console = Console()

params = {
    'publishTestRoot': True,
    'root': "0x34f1add21595c8c2d60a19095a047b4764aee553991ec935d914f367c00ecbff",
    'contentHash': "0x34f1add21595c8c2d60a19095a047b4764aee553991ec935d914f367c00ecbff"
}


def main():
    """
    Connect to badger, distribute assets to specified test user, and keep ganache open.
    Ganache will run with your default brownie settings for mainnet-fork
    """

    # The address to test with
    user = accounts.at(decouple.config("TEST_ACCOUNT"), force=True)

    badger = connect_badger("deploy-final.json", load_deployer=False, load_keeper=False, load_guardian=False)

    # TODO: After prod deployment, just connect instead.
    # claw = deploy_claw_minimal(badger.deployer, printToFile=True)
    # # Deploy claw setts
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

    console.print("[blue]=== 🦡 Test ENV for account {} 🦡 ===[/blue]".format(user))

    tree = badger.badgerTree
    newLogic = BadgerTree.deploy({"from": badger.deployer})

    multi = GnosisSafe(badger.opsMultisig)

    # Upgrade Tree
    multi.execute(
        MultisigTxMetadata(description="Upgrade Tree"),
        {
            "to": badger.opsProxyAdmin.address,
            "data": badger.opsProxyAdmin.upgrade.encode_input(tree, newLogic),
        },
    )

    # Publish test root
    publish_new_root(badger, params["root"], params["contentHash"])


    console.print("[green]=== ✅ Test ENV Setup Complete ✅ ===[/green]")
    # Keep ganache open until closed
    time.sleep(days(365))
