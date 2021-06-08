from helpers.constants import AddressZero, MaxUint256
from helpers.token_utils import (
    BalanceSnapshotter,
    distribute_from_whales,
    distribute_test_ether,
    get_token_balances,
)
from ape_safe import ApeSafe
from brownie import *
from gnosis.safe.safe import Safe
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.registry import registry
from helpers.utils import shares_to_fragments, to_digg_shares, val

from helpers.gnosis_safe import (
    ApeSafeHelper,
    GnosisSafe,
    MultisigTx,
    MultisigTxMetadata,
    convert_to_test_mode,
    exec_direct,
)
from helpers.proxy_utils import deploy_proxy
from helpers.time_utils import days, hours

console = Console()
limit = Wei("100 gwei")

assets = [
    registry.curve.pools.hbtcCrv,
    registry.curve.pools.pbtcCrv,
    registry.curve.pools.obtcCrv,
    registry.curve.pools.bbtcCrv
]

vaults = [
    "0x8c76970747afd5398e958bdfada4cf0b9fca16c4",
    "0x55912d0cf83b75c492e761932abc4db4a5cb1b17",
    "0xf349c0faa80fc1870306ac093f75934078e28991",
    "0x5dce29e92b1b939f8e8c60dcf15bde82a85be4a9"
]

def test_main():
    """
    What contracts are required?
    Sett (Proxy)
    GuestList (Proxy)
    Strategy (Logic + Proxy)

    What addresses do I need?
    Fee splitter
    Mushroom fee address
    All that good stuff
    """
    badger = connect_badger()
    digg = badger.digg
    dev = badger.deployer

    distribute_from_whales(dev, assets=["digg"])
    digg.token.transfer(badger.devMultisig, digg.token.balanceOf(dev), {'from':dev})

    multi = GnosisSafe(badger.devMultisig)
    safe = ApeSafe(badger.devMultisig.address)
    ops = ApeSafe(badger.opsMultisig.address)
    helper = ApeSafeHelper(badger, safe)
    controller = safe.contract("0x9b4efA18c0c6b4822225b81D150f3518160f8609")

    controller.setVault()

    """
    address _token,
    address _controller,
    address _governance,
    address _keeper,
    address _guardian,
    bool _overrideTokenName,
    string memory _namePrefix,
    string memory _symbolPrefix
    """
    
    for i in range(0, len(assets)):
        asset = interface.IERC20(assets[i])
        vault = interface.ISett(vaults[i])

        vault.initialize(
            asset,
            controller,
            badger.devMultisig,
            badger.keeper,
            badger.guardian,
            False,
            "",
            ""
        )

        controller.setVault(asset, vault)