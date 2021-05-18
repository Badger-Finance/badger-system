import pytest
from brownie import (
    chain,
    accounts,
    interface,
    MockVault,
    SettV1,
)

from helpers.constants import AddressZero
from helpers.time_utils import days
from helpers.registry import registry
from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger
from scripts.systems.bridge_system import connect_bridge
from scripts.systems.swap_system import connect_swap
from scripts.upgrade.upgrade_bridge import upgrade_bridge, configure_bridge


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
        # NB: Only deployed to BSC right now. We're testing w/ mock.
        "id": "native.test",
        "symbol": "bwBTC",
        "token": registry.tokens.wbtc,
        "address": AddressZero,
        "upgrade": False,
    },
]


# Tests mint/burn to/from crv sett.
# We create a mock vault for each pool token.
@pytest.mark.parametrize(
    "vault", BRIDGE_VAULTS,
)
def test_bridge_vault(vault):
    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    _deploy_mocks_and_upgrade_bridge(badger, bridge)

    slippage = .03
    amount = 1 * 10**8
    account = accounts[10]

    v = vault["address"]
    if v == AddressZero:
        v = MockVault.deploy(
            vault["id"],
            vault["symbol"],
            vault["token"],
            {"from": badger.deployer}
        ).address
    else:
        interface.ISettAccessControlDefended(v).approveContractAccess(
            bridge.adapter,
            {"from": badger.devMultisig},
        )

        # NB: Temporarily upgrade crv setts (missing depositFor() method)
        if vault["upgrade"]:
            badger.deploy_logic("SettV1", SettV1)
            logic = badger.logic["SettV1"]
            badger.devProxyAdmin.upgrade(
                v,
                logic,
                {"from": badger.governanceTimelock},
            )

    balanceBefore = interface.IERC20(v).balanceOf(account)

    bridge.adapter.setVaultApproval(v, True, {"from": badger.devMultisig})
    bridge.adapter.mint(
        vault["inToken"],
        slippage * 10**4,
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
    # Approve the mock gateway for transfer of underlying token for "mock" burns.
    # NB: In the real world, burns don't require approvals as it's just an internal update the the user's token balance.
    interface.IERC20(registry.tokens.renbtc).approve(
        bridge.mocks.BTC.gateway,
        balance,
        {"from": bridge.adapter}
    )
    bridge.adapter.burn(
        vault["outToken"],
        v,
        slippage * 10**4,
        account.address,
        balance,
        {"from": account},
    )

    assert interface.IERC20(v).balanceOf(account) == 0


# Tests swap router and wbtc mint/burn.
def test_bridge_basic():
    renbtc = registry.tokens.renbtc
    wbtc = registry.tokens.wbtc

    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    _deploy_mocks_and_upgrade_bridge(badger, bridge)

    swap = connect_swap(badger_config.prod_json)
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

    account = accounts[10]
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
    # Approve the mock gateway for transfer of underlying token for "mock" burns.
    # NB: In the real world, burns don't require approvals as it's just an internal update the the user's token balance.
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


def _deploy_mocks_and_upgrade_bridge(badger, bridge):
    # NB: Deploy/use mock gateway
    bridge.deploy_mocks()
    bridge.adapter.setRegistry(
        bridge.mocks.registry,
        {"from": badger.devMultisig},
    )

    # NB: Temporarily upgrade and configure bridge to use curve token wrapper.
    txFilename = upgrade_bridge(badger, bridge)
    chain.sleep(2*days(2))
    badger.governance_execute_transaction(txFilename)
    configure_bridge(badger, bridge)
