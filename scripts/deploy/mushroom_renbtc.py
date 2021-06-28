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

    vault = (
        badger.getSett("experimental.digg").address,
        "StabilizeDiggSett",
        StabilizeDiggSett.abi,
    )
    controller = safe.contract("0x9b4efA18c0c6b4822225b81D150f3518160f8609")
    guestList = VipCappedGuestListBbtcUpgradeable.at(vault.guestList())

    strategy = StabilizeStrategyDiggV1.at("0xA6af1B913E205B8E9B95D3B30768c0989e942316")

    # strategy = StabilizeStrategyDiggV1.deploy({"from": dev})
    # strategy.initialize(
    #     badger.devMultisig,
    #     dev,
    #     controller,
    #     badger.keeper,
    #     badger.guardian,
    #     0,
    #     [stabilizeVault, diggTreasury],
    #     [250, 0, 50, 250],
    #     {"from": dev},
    # )

    # diggTreasury.initialize(strategy, {"from": dev})

    """
    address _governance,
    address _strategist,
    address _controller,
    address _keeper,
    address _guardian,
    uint256 _lockedUntil,
    address[2] memory _vaultConfig,
    uint256[4] memory _feeConfig
    """

    # === Prod Setup ===
    # print("governance", controller.governance())
    # vault.unpause()
    # vault.setController(controller)
    # controller.approveStrategy(digg.token, strategy)
    # controller.setStrategy(digg.token, strategy)

    # print(controller.address)
    # print(vault.address)
    # print(controller.vaults(digg.token))
    # assert controller.vaults(digg.token) == vault
    # assert controller.strategies(digg.token) == strategy

    # assert vault.token() == strategy.want()

    # diggToken = safe.contract(digg.token.address)

    # diggToken.approve(vault, MaxUint256)
    # a = digg.token.balanceOf(badger.devMultisig)
    # assert vault.guestList() == AddressZero
    # vault.setGuestList(guestList)
    # assert vault.guestList() == guestList

    # === Test Actions ===
    assert digg.token.balanceOf(badger.devMultisig) > 1000000
    assert digg.token.allowance(badger.devMultisig, vault) == MaxUint256
    vault.setKeeper(badger.keeper)

    assert vault.keeper() == badger.keeper
    vault.deposit(a // 2)
    tx = vault.earn()

    # vault.earn({"from": badger.keeper})
    strategy.rebalance({"from": badger.keeper})
    vault.withdrawAll()
