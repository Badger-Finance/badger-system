import json
from brownie import accounts, interface

from helpers.registry import token_registry
from config.badger_config import badger_config
from scripts.systems.bridge_minimal import deploy_bridge_minimal


def test_bridge():
    deployer = None
    devProxyAdmin = None
    with open(badger_config.prod_json) as f:
        deploy = json.load(f)
        deployer = accounts.at(deploy["deployer"], force=True)
        devProxyAdmin = accounts.at(deploy["devProxyAdmin"], force=True)

    renbtc = token_registry.renbtc
    wbtc = token_registry.wbtc
    bridge = deploy_bridge_minimal(deployer, devProxyAdmin, test=True)
    router = bridge.swap.router
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

    account = accounts[10]
    balanceBefore = interface.IERC20(wbtc).balanceOf(account)
    # Test mints
    bridge.adapter.mint(
        wbtc,
        slippage * 10**4,
        account.address,
        amount,
        # Darknode args hash/sig optional since gateway is mocked.
        "",
        "",
        {"from": account},
    )
    assert interface.IERC20(wbtc).balanceOf(account) > balanceBefore

    # Test burns
    balanceBefore = interface.IERC20(wbtc).balanceOf(account)
    interface.IERC20(wbtc).approve(bridge.adapter, balanceBefore, {"from": account})
    # Approve the mock gateway for transfer of underlying token for "mock" burns.
    # NB: In the real world, burns don't require approvals as it's just an internal update the the user's token balance.
    interface.IERC20(renbtc).approve(bridge.mocks.BTC.gateway, balanceBefore, {"from": bridge.adapter})

    # Test mints
    bridge.adapter.burn(
        wbtc,
        slippage * 10**4,
        account.address,
        balanceBefore,
        {"from": account},
    )
    assert interface.IERC20(wbtc).balanceOf(account) == 0


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
