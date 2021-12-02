from os import wait
import enum
from sys import version_info
from eth_typing.evm import Address
import pytest
from brownie import (
    ZERO_ADDRESS,
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

from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata


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


#import addresses
coreContract = registry.defidollar.addresses.core
ibbtcContract = registry.defidollar.addresses.ibbtc
peakContract = registry.defidollar.addresses.badgerPeak
wbtcPeakContract = registry.defidollar.addresses.wbtcPeak

class PeakState(enum.Enum):
    Extinct = 1
    Active = 2
    Dormant = 3

#test mint/burn ibbtc using btokens from badger vaults
@pytest.mark.parametrize(
    "vault, poolId", [(BRIDGE_VAULTS[0], 0)], #vaults correspond with poolid on defidollar side
)

def test_bridge_ibbtc_and_zap(vault, poolId):
    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    swap = connect_swap(badger_config.prod_json)
    _upgrade_bridge(badger, bridge)
    bridge.add_existing_swap(swap)
    _deploy_bridge_mocks(badger, bridge)

    yearnWbtc = connect_badger("deploy-final.json")
    wbtcAddr = yearnWbtc.sett_system["vaults"]["yearn.wbtc"]

    renbtc = registry.tokens.renbtc

    slippage = .03
    amount = 1 * 10**8

    v = vault["address"]

    if poolId == 3:
        v = wbtcAddr

    _config_bridge(badger, bridge)

    gov1 = interface.ICore(coreContract).owner()
    interface.ICore(coreContract).setGuestList(ZERO_ADDRESS, {"from": gov1})

    gov2 = interface.IBadgerSettPeak(peakContract).owner()
    interface.IBadgerSettPeak(peakContract).approveContractAccess(bridge.adapter, {"from": gov2})

    gov3 = interface.IBadgerYearnWbtcPeak(wbtcPeakContract).owner()
    interface.IBadgerYearnWbtcPeak(wbtcPeakContract).approveContractAccess(bridge.adapter, {"from": gov3})

    #bCRVibBTC vault permissions
    gov4 = "0xB65cef03b9B89f99517643226d76e286ee999e77"
    interface.IBridgeVault("0xaE96fF08771a109dc6650a1BdCa62F2d558E40af").approveContractAccess(bridge.adapter, {"from": gov4})

    bridgeBalanceBefore = interface.IERC20(renbtc).balanceOf(bridge.adapter)

    #bCRVibBTC vault
    vault2 = "0xaE96fF08771a109dc6650a1BdCa62F2d558E40af"

    #minting
    accountsBalanceBefore = interface.IERC20(vault2).balanceOf(accounts[0].address)
    bridge.adapter.mint(
        vault["inToken"],
        slippage * 10**4,
        accounts[0],
        v,
        vault2,
        True,
        amount,
        # Darknode args hash/sig optional since gateway is mocked.
        "",
        "", 
        {"from": accounts[0]},
    )
    accountsBalanceAfter = interface.IERC20(vault2).balanceOf(accounts[0].address)

    assert accountsBalanceAfter > accountsBalanceBefore

    gatewayBalanceBefore = interface.IERC20(renbtc).balanceOf(bridge.mocks.BTC.gateway)
    bridgeBalance = interface.IERC20(renbtc).balanceOf(bridge.adapter)

    bridge.adapter.setVaultApproval(vault2, True, {"from": badger.devMultisig})

    #burning
    interface.IERC20(vault2).approve(bridge.adapter, accountsBalanceAfter, {"from": accounts[0]})
    interface.IERC20(ibbtcContract).approve(bridge.adapter, accountsBalanceAfter, {"from": accounts[0]})
    interface.IERC20(renbtc).approve(
        bridge.mocks.BTC.gateway,
        amount,
        {"from": bridge.adapter}
    )
    bridge.adapter.burn(
        vault["inToken"],
        v,
        vault2,
        slippage * 10**4,
        accounts[0].address,
        accountsBalanceAfter,
        True,
        {"from": accounts[0]},
    )
    #assert 0 > 0
    assert interface.IERC20(vault2).balanceOf(accounts[0].address) == 0
    assert interface.IERC20(ibbtcContract).balanceOf(accounts[0].address) == 0
    assert interface.IERC20(renbtc).balanceOf(bridge.adapter) - bridgeBalance < 2
    assert interface.IERC20(renbtc).balanceOf(bridge.mocks.BTC.gateway) > gatewayBalanceBefore


#test mint/burn ibbtc using btokens from badger vaults
@pytest.mark.parametrize(
    "vault, poolId", [(BRIDGE_VAULTS[0], 0)], #vaults correspond with poolid on defidollar side
)

def test_bridge_ibbtc(vault, poolId):
    badger = connect_badger(badger_config.prod_json)
    bridge = connect_bridge(badger, badger_config.prod_json)
    swap = connect_swap(badger_config.prod_json)
    _upgrade_bridge(badger, bridge)
    bridge.add_existing_swap(swap)
    _deploy_bridge_mocks(badger, bridge)

    yearnWbtc = connect_badger("deploy-final.json")
    wbtcAddr = yearnWbtc.sett_system["vaults"]["yearn.wbtc"]

    renbtc = registry.tokens.renbtc

    slippage = .03
    amount = 1 * 10**8

    v = vault["address"]

    if poolId == 3:
        v = wbtcAddr

    _config_bridge(badger, bridge)

    gov2 = interface.IBadgerSettPeak(peakContract).owner()
    interface.IBadgerSettPeak(peakContract).approveContractAccess(bridge.adapter, {"from": gov2})

    gov3 = interface.IBadgerYearnWbtcPeak(wbtcPeakContract).owner()
    interface.IBadgerYearnWbtcPeak(wbtcPeakContract).approveContractAccess(bridge.adapter, {"from": gov3})

    bridgeBalanceBefore = interface.IERC20(renbtc).balanceOf(bridge.adapter)

    vault2 = ZERO_ADDRESS

    #minting
    accountsBalanceBefore = interface.IERC20(ibbtcContract).balanceOf(accounts[0].address)
    bridge.adapter.mint(
        vault["inToken"],
        slippage * 10**4,
        accounts[0],
        v,
        vault2,
        True,
        amount,
        # Darknode args hash/sig optional since gateway is mocked.
        "",
        "", 
        {"from": accounts[0]},
    )
    accountsBalanceAfter = interface.IERC20(ibbtcContract).balanceOf(accounts[0].address)

    assert accountsBalanceAfter > accountsBalanceBefore

    gatewayBalanceBefore = interface.IERC20(renbtc).balanceOf(bridge.mocks.BTC.gateway)
    bridgeBalance = interface.IERC20(renbtc).balanceOf(bridge.adapter)

    #burning
    interface.IERC20(ibbtcContract).approve(bridge.adapter, accountsBalanceAfter, {"from": accounts[0]})
    interface.IERC20(renbtc).approve(
        bridge.mocks.BTC.gateway,
        amount,
        {"from": bridge.adapter}
    )
    bridge.adapter.burn(
        vault["inToken"],
        v,
        vault2,
        slippage * 10**4,
        accounts[0].address,
        accountsBalanceAfter,
        True,
        {"from": accounts[0]},
    )

    assert interface.IERC20(ibbtcContract).balanceOf(accounts[0].address) == 0
    assert interface.IERC20(renbtc).balanceOf(bridge.adapter) - bridgeBalance < 2
    assert interface.IERC20(renbtc).balanceOf(bridge.mocks.BTC.gateway) > gatewayBalanceBefore


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
    _upgrade_bridge(badger, bridge)

    slippage = 0.03
    amount = 1 * 10 ** 8

    vault2 = ZERO_ADDRESS

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
                vault2,
                False,
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
                bridge.mocks.BTC.gateway, balance*10, {"from": bridge.adapter}
            )
            bridge.adapter.burn(
                vault["outToken"],
                v,
                vault2,
                slippage * 10 ** 4,
                account.address,
                balance,
                False,
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
                    AddressZero,
                    False,
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
    _upgrade_bridge(badger, bridge)

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
                AddressZero,
                False,
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
                AddressZero,
                slippage * 10 ** 4,
                account.address,
                balance,
                False,
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

def _config_bridge(badger, bridge):
    yearnWbtc = connect_badger("deploy-final.json")
    wbtcAddr = yearnWbtc.sett_system["vaults"]["yearn.wbtc"]

    multi = GnosisSafe(badger.devMultisig)

    multi.execute(
        MultisigTxMetadata(description="add defi dollar contract addresses to adapter contract"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setIbbtcContracts.encode_input(registry.defidollar.addresses.ibbtc, registry.defidollar.addresses.badgerPeak, registry.defidollar.addresses.wbtcPeak),
        },
    )

    for pool in registry.defidollar.pools:
        multi.execute(
            MultisigTxMetadata(description="populate vault/poolid dictionary"),
            {
                "to": bridge.adapter.address,
                "data": bridge.adapter.setVaultPoolId.encode_input(pool.sett, pool.id),
            },
        )

    multi.execute(
        MultisigTxMetadata(description="populate vault/poolid dictionary"),
        {
            "to": bridge.adapter.address,
            "data": bridge.adapter.setVaultPoolId.encode_input(wbtcAddr, 3),
        },
    )