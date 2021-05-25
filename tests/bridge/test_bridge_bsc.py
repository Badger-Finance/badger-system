import pytest
from brownie import (
    accounts,
    interface,
    MockVault,
    BadgerBridgeAdapter,
    CurveSwapStrategy,
    CurveTokenWrapper,
)

from helpers.constants import AddressZero
from helpers.registry import registry
from config.badger_config import badger_config, bridge_config
from scripts.systems.badger_system import connect_badger
from scripts.systems.bridge_minimal import deploy_bridge_minimal
from scripts.systems.swap_system import connect_swap


# Tests swap router failures and btcb mint/burn.
# def test_bridge_basic_swap_fail():
#     renbtc = registry.tokens.renbtc
#     wbtc = registry.tokens.wbtc
#
#     badger = connect_badger(badger_config.prod_json)
#     bridge = deploy_bridge_minimal(
#         badger.deployer,
#         badger.devProxyAdmin,
#         bridge_config,
#         test=True,
#     )
#     swap = bridge.swap
#
#     # NB: If true, fails during router opimizeSwap() call, otherwise the underlying strategy fails.
#     for router_fail in [True, False]:
#         _deploy_swap_mocks(badger, bridge, swap, router_fail=router_fail)
#
#         # .1% slippage
#         slippage = .001
#         amount = 1 * 10**8
#
#         for accIdx in range(10, 12):
#             account = accounts[accIdx]
#             for i in range(0, 2):
#                 balanceBefore = interface.IERC20(renbtc).balanceOf(account)
#                 # Test mints
#                 bridge.adapter.mint(
#                     wbtc,
#                     slippage * 10**4,
#                     account.address,
#                     AddressZero,  # No vault.
#                     amount,
#                     # Darknode args hash/sig optional since gateway is mocked.
#                     "",
#                     "",
#                     {"from": account},
#                 )
#                 assert interface.IERC20(renbtc).balanceOf(account) > balanceBefore
#                 # NB: User should not receive any wbtc but rather renbtc as part
#                 # of the fallback mechanism.
#                 assert interface.IERC20(wbtc).balanceOf(account) == 0


# Tests swap router and wbtc mint/burn.
def test_bridge_basic():
    renbtc = registry.tokens.renbtc
    wbtc = registry.tokens.wbtc

    badger = connect_badger(badger_config.prod_json)
    bridge = deploy_bridge_minimal(
        badger.deployer,
        badger.devProxyAdmin,
        bridge_config,
        test=True,
    )
    swap = bridge.swap

    router = swap.router
    # 3% slippage
    slippage = .03
    amount = 1 * 10**8
    # Test estimating slippage from a random account for wbtc <-> renbtc swaps.
    _assert_swap_slippage(
        router,
        renbtc,
        wbtc,
        amount,
        slippage,
    )
    _assert_swap_slippage(
        router,
        wbtc,
        renbtc,
        amount,
        slippage,
    )

    for accIdx in range(10, 12):
        account = accounts[accIdx]
        for i in range(0, 2):
            balanceBefore = interface.IERC20(wbtc).balanceOf(account)
            # Test mints
            bridge.adapter.mint(
                wbtc,
                slippage * 10**4,
                account.address,
                AddressZero,  # No vault.
                amount,
                # Darknode args hash/sig optional since gateway is mocked.
                "",
                "",
                {"from": account},
            )
            assert interface.IERC20(wbtc).balanceOf(account) > balanceBefore

            # Test burns
            balance = interface.IERC20(wbtc).balanceOf(account)
            interface.IERC20(wbtc).approve(bridge.adapter, balance, {"from": account})
            # Approve mock gateway for transfer of underlying token for "mock" burns.
            # NB: In the real world, burns don't require approvals as it's
            # just an internal update the the user's token balance.
            interface.IERC20(renbtc).approve(
                bridge.mocks.BTC.gateway,
                balance,
                {"from": bridge.adapter},
            )

            bridge.adapter.burn(
                wbtc,
                AddressZero,  # No vault.
                slippage * 10**4,
                account.address,
                balance,
                {"from": account},
            )
            assert interface.IERC20(wbtc).balanceOf(account) == 0


def test_bridge_sweep():
    renbtc = registry.tokens.renbtc
    wbtc = registry.tokens.wbtc

    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    _upgrade_bridge(badger, bridge)

    # Send both renbtc and wbtc to bridge adapter and test sweep.
    for (whale, token) in [
        (registry.whales.renbtc.whale, interface.IERC20(renbtc)),
        (registry.whales.wbtc.whale, interface.IERC20(wbtc)),
    ]:
        token.transfer(
            bridge.adapter,
            token.balanceOf(whale),
            {"from": whale},
        )
        # Can be called from any account, should always send to governance.
        beforeBalance = token.balanceOf(badger.devMultisig)
        bridge.adapter.sweep({"from": badger.devMultisig})
        assert token.balanceOf(badger.devMultisig) > beforeBalance


def _assert_swap_slippage(router, fromToken, toToken, amountIn, slippage):
    # Should be accessible from a random account.
    account = accounts[8]
    (strategyAddr, amountOut) = router.optimizeSwap.call(
        fromToken,
        toToken,
        amountIn,
        {"from": account},
    )
    assert (1 - (amountOut / amountIn)) < slippage
    strategy = interface.ISwapStrategy(strategyAddr)
    # Redundant slippage check, but just to be sure.
    amountOut = strategy.estimateSwapAmount.call(
        fromToken,
        toToken,
        amountIn,
        {"from": account},
    )
    assert (1 - (amountOut / amountIn)) < slippage


def _deploy_swap_mocks(badger, bridge, swap, router_fail=False):
    swap.deploy_mocks(router_fail=router_fail)
    bridge.adapter.setRouter(swap.mocks.router, {"from": badger.devMultisig})
