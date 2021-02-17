import json
from brownie import accounts

from config.badger_config import badger_config
from scripts.systems.bridge_minimal import deploy_bridge_minimal


def test_bridge():
    deployer = None
    with open(badger_config.prod_json) as f:
        deploy = json.load(f)
        deployer = accounts.at(deploy["deployer"], force=True)

    deploy_bridge_minimal(deployer, test=True)
