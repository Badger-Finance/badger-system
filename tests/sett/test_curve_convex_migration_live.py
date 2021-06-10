from helpers.time_utils import days
import json
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.registry import registry
from helpers.registry.artifacts import artifacts
from collections import namedtuple
from config.badger_config import badger_config, digg_config, sett_config
from scripts.systems.badger_system import connect_badger
from scripts.systems.constants import SettType
from helpers.token_utils import distribute_test_ether, distribute_from_whales
from rich.console import Console
from helpers.proxy_utils import deploy_proxy
from helpers.utils import approx

console = Console()

@pytest.fixture(scope="module", autouse=True)
def setup(
    StrategyConvexLpOptimizer,
):
    # Assign accounts
    with open(digg_config.prod_json) as f:
        badger_deploy = json.load(f)
        deployer = accounts.at(badger_deploy["deployer"], force=True)
        guardian = accounts.at(badger_deploy["guardian"], force=True)
        keeper = accounts.at(badger_deploy["keeper"], force=True)
        governance = accounts.at(badger_deploy["timelock"], force=True)

    strategist = accounts[3]
    user1 = accounts[4]
    user2 = accounts[5]
    user3 = accounts[6]

    namedAccounts = {
        "deployer": deployer,
        "guardian": guardian,
        "keeper": keeper,
        "governance": governance,
        "strategist": strategist,
        "user1": user1,
        "user2": user2,
        "user3": user3,
    }

    # Setup Badger system
    badger = connect_badger(badger_config.prod_json)
    distribute_test_ether(deployer, Wei("20 ether"))

    # Key of Sett to migrate
    settKey = "native.renCrv"

    # Connect to prod controller and vault
    vault = badger.sett_system.vaults[settKey]
    print("Vault for " + settKey + " fetched with address " + vault.address)

    controller = interface.IController(vault.controller())
    print("Controller for " + settKey + " fetched with address " + controller.address)

    # Deploy and initialize the strategy
    params = sett_config.native.convexRenCrv.params
    want = sett_config.native.convexRenCrv.params.want

    contract = StrategyConvexLpOptimizer.deploy({"from": deployer})
    strategy = deploy_proxy(
        "StrategyConvexLpOptimizer",
        StrategyConvexLpOptimizer.abi,
        contract.address,
        web3.toChecksumAddress(badger.devProxyAdmin.address),
        contract.initialize.encode_input(
            governance.address,
            strategist.address,
            controller.address,
            keeper.address,
            guardian.address, 
            [params.want, badger.badgerTree.address, params.gauge,],
            params.pid,
            [
                params.performanceFeeGovernance,
                params.performanceFeeStrategist,
                params.withdrawalFee,
            ],
        ),
        deployer,
    )

    # Finish setup

    yield namedtuple(
        "setup", "badger controller vault strategy namedAccounts"
    )(badger, controller, vault, strategy, namedAccounts)


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

# @pytest.mark.skip()
def test_strategy_migration(setup):
    # Get Actors:
    user1 = setup.namedAccounts["user1"]
    user2 = setup.namedAccounts["user2"]
    user3 = setup.namedAccounts["user3"]
    deployer = setup.namedAccounts["deployer"]
    guardian = setup.namedAccounts["guardian"]
    keeper = setup.namedAccounts["keeper"]
    governance = setup.namedAccounts["governance"]
    strategist = setup.namedAccounts["strategist"]

    # Get System, Controller, Vault and Strategy
    badger = setup.badger
    controller = setup.controller
    vault = setup.vault
    strategy = setup.strategy

    # Get current strategy and want
    want = interface.IERC20(vault.token())
    currentStrategy = interface.IStrategy(controller.strategies(want.address))

    # === Pre migration checks === #

    # New Strategy's and currentStrategy's want matches vault's token
    assert strategy.want() == want.address
    assert currentStrategy.want() == want.address
    # Current strategy for want is not new strategy
    assert currentStrategy.address != strategy.address
    # Balance of Sett (Balance on Sett, Controller and Strategy) is greater than 0
    initialSettBalance = vault.balance()
    assert initialSettBalance > 0
    # Balance of vault equals to the Sett's balance minus strategy balance
    assert want.balanceOf(vault.address) == initialSettBalance - currentStrategy.balanceOf()
    # Balance of current Strategy matches balance of Sett
    assert initialSettBalance == currentStrategy.balanceOf()
    # Balance of new Strategy starts off at 0
    assert strategy.balanceOf() == 0

    # Print initial balances:
    print("=== Initial Balances ===")
    print("Sett: ", initialSettBalance)
    print("Vault: ", want.balanceOf(vault.address))
    print("Old Strategy: ", currentStrategy.balanceOf())
    print("New Strategy: ", strategy.balanceOf())


    # === Migration === #

    # Approve new strategy for want on Controller
    controller.approveStrategy(strategy.want(), strategy.address, {"from": governance})
    assert controller.approvedStrategies(strategy.want(), strategy.address)

    # Set new strategy for want on Controller
    controller.setStrategy(strategy.want(), strategy.address, {"from": governance})


    # === Post migration checks === #

    # Check that the new Strategy is the active Strategy for want on Controller
    assert controller.strategies(vault.token()) == strategy.address
    # Balance of Sett remains the same
    assert initialSettBalance == vault.balance()
    # Balance of vault equals to the whole Sett balance since controller withdraws all of want
    # and this is transfered to the vault.
    assert want.balanceOf(vault.address) == initialSettBalance
    # Balance of old Strategy goes down to 0
    assert currentStrategy.balanceOf() == 0
    # Balance of new Strategy starts off at 0
    assert strategy.balanceOf() == 0

    # Print final balances:
    print("=== Final Balances ===")
    print("Sett: ", vault.balance())
    print("Vault: ", want.balanceOf(vault.address))
    print("Old Strategy: ", currentStrategy.balanceOf())
    print("New Strategy: ", strategy.balanceOf())


# @pytest.mark.skip()
def test_post_migration_flow(setup):
    # Get Actors:
    user1 = setup.namedAccounts["user1"]
    user2 = setup.namedAccounts["user2"]
    user3 = setup.namedAccounts["user3"]
    deployer = setup.namedAccounts["deployer"]
    guardian = setup.namedAccounts["guardian"]
    keeper = setup.namedAccounts["keeper"]
    governance = setup.namedAccounts["governance"]
    strategist = setup.namedAccounts["strategist"]

    # Get System, Controller, Vault and Strategy
    badger = setup.badger
    controller = setup.controller
    vault = setup.vault
    strategy = setup.strategy

    # Get current strategy and want
    want = interface.IERC20(vault.token())
    currentStrategy = interface.IStrategy(controller.strategies(want.address))


    # === Migration === #

    # Approve new strategy for want on Controller
    controller.approveStrategy(strategy.want(), strategy.address, {"from": governance})
    assert controller.approvedStrategies(strategy.want(), strategy.address)

    # Set new strategy for want on Controller
    controller.setStrategy(strategy.want(), strategy.address, {"from": governance})
    assert controller.strategies(vault.token()) == strategy.address


    # === Post Migration Strategy Flow == #

    # Transfer assets to users
    distribute_from_whales(user1, 1, "renCrv")

    startingBalance = want.balanceOf(user1)
    assert startingBalance > 0
    want.transfer(user2.address, startingBalance/3, {"from": user1})
    want.transfer(user3.address, startingBalance/3, {"from": user1})

    startingBalance1 = want.balanceOf(user1)
    startingBalance2 = want.balanceOf(user2)
    startingBalance3 = want.balanceOf(user3)
    startingBalanceVault = want.balanceOf(vault.address)

    print("=== Initial Balances ===")
    print("User1: ", startingBalance1/Wei("1 ether"))
    print("Vault: ", startingBalanceVault/Wei("1 ether"))

    # Deposit

    # User1 has 0 shares
    assert vault.balanceOf(user1.address) == 0

    want.approve(vault.address, MaxUint256, {"from": user1})
    depositAmount = startingBalance1/2
    vault.deposit(depositAmount, {"from": user1})

    # Want is deposited correctly
    assert want.balanceOf(vault.address) == startingBalanceVault + depositAmount
    # Right amount of shares is minted
    assert approx(
        vault.balanceOf(user1.address), 
        (depositAmount // vault.getPricePerFullShare()) * (10**vault.decimals()), 
        1
    )
    # Want balance of user1 decreases by depositAmount
    assert want.balanceOf(user1.address) == startingBalance1 - depositAmount

    chain.sleep(days(1))
    chain.mine()

    # Earn
    prevBalanceOfPool = strategy.balanceOfPool()
    prevBalanceOfWant = strategy.balanceOfWant()
    prevTotalBalance = strategy.balanceOf() 

    vault.earn({"from": deployer}) # deployer set as keeper for this Sett

    # All want should be in pool OR sitting in strategy, not a mix
    assert (
        strategy.balanceOfWant() == 0 and strategy.balanceOfPool() > prevBalanceOfPool
    ) or (
        strategy.balanceOfPool() == 0 and strategy.balanceOfWant() > prevBalanceOfWant
    )

    # Total want balance within strategy increases (pool + strategy)
    assert strategy.balanceOf() > prevTotalBalance
    # Balance of user remains the same
    assert want.balanceOf(user1.address) == startingBalance1 - depositAmount




