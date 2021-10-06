import brownie
import json
import pytest
from brownie import KeeperAccessControl, interface
from dotmap import DotMap

from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger


KEEPER = "0xf8dbb94608e72a3c4ceeab4ad495ac51210a341e"


def upgrade_logic(badger, proxy, name, artifact):
    # Deploy new logic
    badger.deploy_logic(name, artifact)
    logic = badger.logic[name]

    badger.testProxyAdmin.upgrade(
        proxy,
        logic,
        {"from": badger.testMultisig},
    )


@pytest.fixture()
def badger():
    return connect_badger(badger_config.prod_json)


@pytest.fixture()
def mstable_voter_proxy():
    with open(badger_config.prod_json) as f:
        deployed = DotMap(json.load(f))
        return deployed.mstable.MStableVoterProxy

@pytest.fixture()
def mStable_strategy():
    return "0xd409c506742b7f76f164909025ab29a47e06d30a" # imBTC Strategy

@pytest.fixture()
def mta():
    return interface.IERC20("0xa3bed4e1c75d00fa6f4e5e6922db7261b5e9acd2") # mta token


def test_upgrade_keeper_acl(badger, mstable_voter_proxy, mta, mStable_strategy):
    # NOTE: Ideally should get deployed contract/abi from etherscan,
    #       but Contract.from_explorer() doesn't seem to work
    keeper_acl = badger.keeperAccessControl

    with brownie.reverts():
        keeper_acl.harvestMta(mstable_voter_proxy, {"from": KEEPER})

    upgrade_logic(
        badger,
        keeper_acl,
        "KeeperAccessControl",
        KeeperAccessControl,
    )

    before = mta.balanceOf(mStable_strategy)

    keeper_acl.harvestMta(mstable_voter_proxy, {"from": KEEPER})

    assert mta.balanceOf(mStable_strategy) > before