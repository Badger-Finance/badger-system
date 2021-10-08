from helpers.proxy_utils import deploy_proxy
from scripts.systems.badger_system import connect_badger
from brownie import *
from config.badger_config import badger_config

KEEPER = "0xF8dbb94608E72A3C4cEeAB4ad495ac51210a341e"
KEEPER_ACL = "0x711A339c002386f9db409cA55b6A35a604aB6cF6"


def main():
    badger = connect_badger(badger_config.prod_json)
    deployer = badger.deployer

    flashbots_harvester = FlashbotsHarvester.deploy({"from": deployer})
    proxy = deploy_proxy(
        "FlashbotsHarvester",
        flashbots_harvester.abi,
        flashbots_harvester.address,
        badger.testProxyAdmin.address,
        flashbots_harvester.initialize.encode_input(
            deployer,
            KEEPER,
            KEEPER_ACL,
        ),
        deployer,
    )
