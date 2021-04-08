import json
import pytest
from brownie import (
    accounts,
    interface,
    MockVault,
)

from helpers.constants import AddressZero
from helpers.registry import token_registry, whale_registry
from helpers.token_utils import distribute_from_whale
from config.badger_config import badger_config
from scripts.systems.bridge_minimal import deploy_bridge_minimal


RENBTC = "0x49849C98ae39Fff122806C06791Fa73784FB3675"
TBTC = "0x64eda51d3Ad40D56b9dFc5554E06F94e1Dd786Fd"
SBTC = "0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3"
# Bridge mock vaults for testing.
# Schema is (in token addr, vault name, vault symbol, vault token addr)
BRIDGE_VAULTS = [
    # TODO: When bridge adapter addr is approved, can test
    # directly against badger sett contracts.
    {
        "inToken": token_registry.renbtc,
        "name": "curve renbtc sett",
        "symbol": "bcrvrenBTC",
        "token": RENBTC,
    },
    {
        "inToken": token_registry.renbtc,
        "name": "curve tbtc sett",
        "symbol": "bcrvtBTC",
        "token": TBTC,
    },
    {
        "inToken": token_registry.renbtc,
        "name": "curve sbtc sett",
        "symbol": "bcrvsBTC",
        "token": SBTC,
    },
    {
        "inToken": token_registry.wbtc,
        "name": "yearn wbtc sett",
        "symbol": "bwBTC",
        "token": token_registry.wbtc,
    },
]


# Tests mint/burn to/from crv sett.
# We create a mock vault for each pool token.
@pytest.mark.parametrize(
    "vault", BRIDGE_VAULTS,
)
def test_bridge_vault(vault):
    deployer, devProxyAdmin = _load_accounts()
    bridge = deploy_bridge_minimal(deployer, devProxyAdmin, test=True)

    slippage = .03
    amount = 1 * 10**8
    account = accounts[10]

    mockVault = MockVault.deploy(
        vault["name"],
        vault["symbol"],
        vault["token"],
        {"from": deployer}
    )
    balanceBefore = interface.IERC20(mockVault).balanceOf(account)

    bridge.adapter.setVaultApproval(mockVault, True, {"from": deployer})
    bridge.adapter.mint(
        vault["inToken"],
        slippage * 10**4,
        account.address,
        mockVault.address,
        amount,
        # Darknode args hash/sig optional since gateway is mocked.
        "",
        "",
        {"from": account},
    )
    assert interface.IERC20(mockVault).balanceOf(account) > balanceBefore


# Tests swap router and wbtc mint/burn.
def test_bridge_basic():
    deployer, devProxyAdmin = _load_accounts()

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
        AddressZero,  # No vault.
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
        AddressZero,  # No vault.
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


# loads deployer and dev proxy admin accounts
def _load_accounts():
    with open(badger_config.prod_json) as f:
        deploy = json.load(f)
        deployer = accounts.at(deploy["deployer"], force=True)
        devProxyAdmin = accounts.at(deploy["devProxyAdmin"], force=True)
        return deployer, devProxyAdmin
