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
from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger
from scripts.systems.bridge_system import connect_bridge
from scripts.systems.swap_system import connect_swap


# Curve lp tokens
RENBTC = "0x49849C98ae39Fff122806C06791Fa73784FB3675"
TBTC = "0x64eda51d3Ad40D56b9dFc5554E06F94e1Dd786Fd"
SBTC = "0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3"
# Bridge mock vaults for testing.
# Schema is (in token addr, vault name, vault symbol, vault token addr)
BRIDGE_VAULTS = [
    # TODO: When bridge adapter addr is approved, can test
    # directly against badger sett contracts.
    {
        "inToken": registry.tokens.renbtc,
        "outToken": registry.tokens.renbtc,
        "id": "native.renCrv",
        "symbol": "bcrvrenBTC",
        "token": RENBTC,
        "address": "0x6dEf55d2e18486B9dDfaA075bc4e4EE0B28c1545",
        "upgrade": True,
    },
    {
        "inToken": registry.tokens.renbtc,
        "outToken": registry.tokens.renbtc,
        "id": "native.tbtcCrv",
        "symbol": "bcrvtBTC",
        "token": TBTC,
        "address": "0xb9D076fDe463dbc9f915E5392F807315Bf940334",
        "upgrade": True,
    },
    {
        "inToken": registry.tokens.renbtc,
        "outToken": registry.tokens.renbtc,
        "id": "native.sbtcCrv",
        "symbol": "bcrvsBTC",
        "token": SBTC,
        "address": "0xd04c48A53c111300aD41190D63681ed3dAd998eC",
        "upgrade": True,
    },
    {
        "inToken": registry.tokens.wbtc,
        "outToken": registry.tokens.wbtc,
        "id": "yearn.wbtc",
        "symbol": "byvwBTC",
        "token": registry.tokens.wbtc,
        "address": "0x4b92d19c11435614cd49af1b589001b7c08cd4d5",
        "upgrade": False,
    },
]


# Tests mint/burn to/from crv sett.
# We create a mock vault for each pool token.
@pytest.mark.parametrize(
    "vault",
    BRIDGE_VAULTS,
)
def test_bridge_vault(vault):
    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    swap = connect_swap(badger_config.prod_json)
    bridge.add_existing_swap(swap)
    _deploy_bridge_mocks(badger, bridge)

    slippage = 0.03
    amount = 1 * 10 ** 8

    v = vault["address"]
    # TODO: Can interleave these mints/burns.
    for accIdx in range(10, 12):
        account = accounts[accIdx]
        for i in range(0, 2):
            balanceBefore = interface.IERC20(v).balanceOf(account)

            bridge.adapter.mint(
                vault["inToken"],
                slippage * 10 ** 4,
                account.address,
                v,
                amount,
                # Darknode args hash/sig optional since gateway is mocked.
                "",
                "",
                {"from": account},
            )
            balance = interface.IERC20(v).balanceOf(account)
            assert balance > balanceBefore

            interface.IERC20(v).approve(
                bridge.adapter.address,
                balance,
                {"from": account},
            )
            # Approve mock gateway for transfer of underlying token for "mock" burns.
            # NB: In the real world, burns don't require approvals as it's just
            # an internal update the the user's token balance.
            interface.IERC20(registry.tokens.renbtc).approve(
                bridge.mocks.BTC.gateway, balance, {"from": bridge.adapter}
            )
            bridge.adapter.burn(
                vault["outToken"],
                v,
                slippage * 10 ** 4,
                account.address,
                balance,
                {"from": account},
            )

            assert interface.IERC20(v).balanceOf(account) == 0


# Tests swap router failures and wbtc mint/burn.
def test_bridge_basic_swap_fail():
    renbtc = registry.tokens.renbtc
    wbtc = registry.tokens.wbtc

    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    swap = connect_swap(badger_config.prod_json)
    bridge.add_existing_swap(swap)
    _upgrade_bridge(badger, bridge)
    _deploy_bridge_mocks(badger, bridge)

    # NB: If true, fails during router opimizeSwap() call, otherwise the underlying strategy fails.
    for router_fail in [True, False]:
        _deploy_swap_mocks(badger, bridge, swap, router_fail=router_fail)

        # .1% slippage
        slippage = 0.001
        amount = 1 * 10 ** 8

        for accIdx in range(10, 12):
            account = accounts[accIdx]
            for i in range(0, 2):
                balanceBefore = interface.IERC20(renbtc).balanceOf(account)
                # Test mints
                bridge.adapter.mint(
                    wbtc,
                    slippage * 10 ** 4,
                    account.address,
                    AddressZero,  # No vault.
                    amount,
                    # Darknode args hash/sig optional since gateway is mocked.
                    "",
                    "",
                    {"from": account},
                )
                assert interface.IERC20(renbtc).balanceOf(account) > balanceBefore
                # NB: User should not receive any wbtc but rather renbtc as part
                # of the fallback mechanism.
                assert interface.IERC20(wbtc).balanceOf(account) == 0


# Tests swap router and wbtc mint/burn.
def test_bridge_basic():
    renbtc = registry.tokens.renbtc
    wbtc = registry.tokens.wbtc

    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    swap = connect_swap(badger_config.prod_json)
    bridge.add_existing_swap(swap)
    _deploy_bridge_mocks(badger, bridge)

    router = swap.router
    # 3% slippage
    slippage = 0.03
    amount = 1 * 10 ** 8
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
                slippage * 10 ** 4,
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
                slippage * 10 ** 4,
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


def _deploy_bridge_mocks(badger, bridge):
    # NB: Deploy/use mock gateway
    bridge.deploy_mocks()
    bridge.adapter.setRegistry(
        bridge.mocks.registry,
        {"from": badger.devMultisig},
    )


def _deploy_swap_mocks(badger, bridge, swap, router_fail=False):
    swap.deploy_mocks(router_fail=router_fail)
    bridge.adapter.setRouter(swap.mocks.router, {"from": badger.devMultisig})


def _upgrade_swap(badger, swap):
    badger.deploy_logic("CurveSwapStrategy", CurveSwapStrategy)
    logic = badger.logic["CurveSwapStrategy"]
    badger.devProxyAdmin.upgrade(
        swap.strategies.curve,
        logic,
        {"from": badger.governanceTimelock},
    )


def _upgrade_bridge(badger, bridge):
    badger.deploy_logic("BadgerBridgeAdapter", BadgerBridgeAdapter)
    logic = badger.logic["BadgerBridgeAdapter"]
    badger.devProxyAdmin.upgrade(
        bridge.adapter,
        logic,
        {"from": badger.governanceTimelock},
    )

    badger.deploy_logic("CurveTokenWrapper", CurveTokenWrapper)
    logic = badger.logic["CurveTokenWrapper"]
    bridge.adapter.setCurveTokenWrapper(logic, {"from": badger.devMultisig})
