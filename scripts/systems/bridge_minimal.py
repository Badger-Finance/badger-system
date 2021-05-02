from brownie import BadgerBridgeAdapter

from .bridge_system import BridgeSystem
from .swap_system import SwapSystem
from config.badger_config import (
    swap_config,
    bridge_config,
)


def deploy_bridge_minimal(
    deployer, devProxyAdmin, test=False, publish_source=False
) -> BridgeSystem:
    bridge = BridgeSystem(
        deployer, devProxyAdmin, bridge_config, publish_source=publish_source
    )

    swap = SwapSystem(
        deployer, devProxyAdmin, swap_config, publish_source=publish_source
    )
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
    bridge.deploy_adapter(
        registry, swap.router, deployer,
    )
    bridge.deploy_curve_token_wrapper()
    bridge.adapter.setCurveTokenWrapper(bridge.curveTokenWrapper, {"from": deployer})
    bridge.add_existing_swap(swap)
    # Grant strategy swapper role to bridge adapter.
    swap.configure_strategies_grant_swapper_role(bridge.adapter.address)

    return bridge
