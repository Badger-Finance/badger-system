from brownie import accounts, BadgerBridgeAdapter

from .bridge_system import BridgeSystem
from .swap_system import SwapSystem
from config.badger_config import (
    swap_config,
    bridge_config,
)


def deploy_bridge_minimal(deployer, test=False) -> BridgeSystem:
    bridge = BridgeSystem(deployer, bridge_config)

    accounts.at(swap_config.admin, force=True)

    swap = SwapSystem(deployer, swap_config)
    swap.deploy_logic()
    swap.deploy_router()
    swap.deploy_curve_swap_strategy()
    swap.configure_router()

    # Deploy mocks if test mode.
    registry = bridge_config.registry

    if test:
        bridge.deploy_mocks()
        registry = bridge.mocks.registry

    bridge.deploy_logic("BadgerBridgeAdapter", BadgerBridgeAdapter, test=test)
    bridge.deploy_bridge(
        registry,
        swap.router,
    )

    return bridge
