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
from decimal import Decimal

console = Console()


@pytest.fixture(scope="module", autouse=True)
def setup(
    StrategyConvexStakingOptimizer,
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

    # Key of Sett to migrate (ONLY UNCOMMENT THE ONE TO TEST):

    settKey = "native.renCrv"
    # settKey = "native.sbtcCrv"
    # settKey = "native.tbtcCrv"

    # Connect to prod controller and vault
    vault = badger.sett_system.vaults[settKey]
    print("Vault for " + settKey + " fetched with address " + vault.address)

    controller = interface.IController(vault.controller())
    print("Controller for " + settKey + " fetched with address " + controller.address)

    # Deploy and initialize the strategy
    if settKey == "native.renCrv":
        params = sett_config.native.convexRenCrv.params
        want = sett_config.native.convexRenCrv.params.want
        # Transfer assets to users
        distribute_from_whales(user1, 1, "renCrv")
    if settKey == "native.sbtcCrv":
        params = sett_config.native.convexSbtcCrv.params
        want = sett_config.native.convexSbtcCrv.params.want
        # Transfer assets to users
        distribute_from_whales(user1, 1, "sbtcCrv")
    if settKey == "native.tbtcCrv":
        params = sett_config.native.convexTbtcCrv.params
        want = sett_config.native.convexTbtcCrv.params.want
        # Transfer assets to users
        distribute_from_whales(user1, 1, "tbtcCrv")

    contract = StrategyConvexStakingOptimizer.deploy({"from": deployer})
    strategy = deploy_proxy(
        "StrategyConvexStakingOptimizer",
        StrategyConvexStakingOptimizer.abi,
        contract.address,
        web3.toChecksumAddress(badger.devProxyAdmin.address),
        contract.initialize.encode_input(
            governance.address,
            strategist.address,
            controller.address,
            keeper.address,
            guardian.address,
            [
                params.want,
                badger.badgerTree.address,
                params.cvxHelperVault,
                params.cvxCrvHelperVault,
            ],
            params.pid,
            [
                params.performanceFeeGovernance,
                params.performanceFeeStrategist,
                params.withdrawalFee,
            ],
            (
                params.curvePool.swap,
                params.curvePool.wbtcPosition,
                params.curvePool.numElements,
            ),
        ),
        deployer,
    )

    # Finish setup

    yield namedtuple("setup", "badger controller vault strategy namedAccounts")(
        badger, controller, vault, strategy, namedAccounts
    )


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


@pytest.mark.skip()
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
    assert (
        want.balanceOf(vault.address)
        == initialSettBalance - currentStrategy.balanceOf()
    )
    # Balance of new Strategy starts off at 0
    assert strategy.balanceOf() == 0

    # PPS before migration
    pps = vault.getPricePerFullShare()

    # Print initial balances:
    print("=== Initial Balances ===")
    print("Sett: ", initialSettBalance)
    print("Vault: ", want.balanceOf(vault.address))
    print("Old Strategy: ", currentStrategy.balanceOf())
    print("New Strategy: ", strategy.balanceOf())
    print("Vault's PPS: ", vault.getPricePerFullShare())

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
    # PPS remain the same post migration
    assert pps == vault.getPricePerFullShare()

    # Print final balances:
    print("=== Final Balances ===")
    print("Sett: ", vault.balance())
    print("Vault: ", want.balanceOf(vault.address))
    print("Old Strategy: ", currentStrategy.balanceOf())
    print("New Strategy: ", strategy.balanceOf())
    print("Vault's PPS: ", vault.getPricePerFullShare())

    # assert False


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

    cvxHelper = badger.getSett("native.cvx")
    cvxCrvHelper = badger.getSett("native.cvxCrv")

    helper_governance = accounts.at(cvxHelper.governance(), force=True)

    # Approve Strategy to deposit in Helpers
    cvxHelper.approveContractAccess(strategy, {"from": helper_governance})
    cvxCrvHelper.approveContractAccess(strategy, {"from": helper_governance})

    # Get strategy's actors
    stratGov = accounts.at(strategy.governance(), force=True)
    stratKeeper = accounts.at(strategy.keeper(), force=True)
    console.print("Actors", stratGov, stratKeeper)

    # Get current strategy, want and tokens of interest
    want = interface.IERC20(vault.token())
    crv = interface.IERC20(strategy.crv())
    cvx = interface.IERC20(strategy.cvx())
    cvxCrv = interface.IERC20(strategy.cvxCrv())

    currentStrategy = interface.IStrategy(controller.strategies(want.address))

    def print_want_balances(event):
        print("=== Want Balances: " + event + " ===")
        print("User1: ", want.balanceOf(user1) / Wei("1 ether"))
        print("User2: ", want.balanceOf(user2) / Wei("1 ether"))
        print("User3: ", want.balanceOf(user3) / Wei("1 ether"))
        print("Vault: ", want.balanceOf(vault.address) / Wei("1 ether"))
        print("Strat: ", want.balanceOf(strategy.address) / Wei("1 ether"))
        print("Controller: ", want.balanceOf(controller.address) / Wei("1 ether"))

    def print_rewards_lp_balances(event):
        print("=== Rewards/LP Balances: " + event + " ===")
        print("Strat_crv: ", crv.balanceOf(strategy.address) / Wei("1 ether"))
        print("Strat_cvx: ", cvx.balanceOf(strategy.address) / Wei("1 ether"))
        print("Strat_cvxCrv: ", cvxCrv.balanceOf(strategy.address) / Wei("1 ether"))

    # === Migration === #

    # Approve new strategy for want on Controller
    controller.approveStrategy(strategy.want(), strategy.address, {"from": governance})
    assert controller.approvedStrategies(strategy.want(), strategy.address)

    # Set new strategy for want on Controller
    controller.setStrategy(strategy.want(), strategy.address, {"from": governance})
    assert controller.strategies(vault.token()) == strategy.address

    # Match vault and strategy's controller if needed
    if vault.controller() != strategy.controller():
        strategy.setController(vault.controller(), {"from": stratGov})

    print("=== Migration Successful ===")

    # === Post Migration Strategy Flow == #

    startingBalance = want.balanceOf(user1)
    assert startingBalance > 0
    want.transfer(user2.address, startingBalance / 3, {"from": user1})
    want.transfer(user3.address, startingBalance / 3, {"from": user1})

    startingBalance1 = want.balanceOf(user1)
    startingBalanceVault = want.balanceOf(vault.address)

    print_want_balances("Start")
    print_rewards_lp_balances("Start")

    # Deposit
    # User1 has 0 shares
    assert vault.balanceOf(user1.address) == 0

    want.approve(vault.address, MaxUint256, {"from": user1})
    depositAmount = startingBalance1 / 2
    vault.deposit(depositAmount, {"from": user1})

    # Want is deposited correctly
    assert want.balanceOf(vault.address) == startingBalanceVault + depositAmount
    # Right amount of shares is minted
    sharesUser1 = (depositAmount / vault.getPricePerFullShare()) * (
        10 ** vault.decimals()
    )
    assert approx(vault.balanceOf(user1.address), sharesUser1, 1)
    # Want balance of user1 decreases by depositAmount
    assert want.balanceOf(user1.address) == startingBalance1 - depositAmount

    chain.sleep(days(1))
    chain.mine()

    print_want_balances("After user1 deposits " + str(depositAmount / Wei("1 ether")))

    # Earn
    prevBalanceOfPool = strategy.balanceOfPool()
    prevBalanceOfWant = strategy.balanceOfWant()
    prevTotalBalance = strategy.balanceOf()

    tx = vault.earn({"from": deployer})  # deployer set as keeper for this Sett
    print("Earn Event:", tx)

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

    print_want_balances("After earn() is called")
    print_rewards_lp_balances("After earn() is called")

    chain.sleep(days(1))
    chain.mine()

    # Tend 1
    prevCvxBalance = cvx.balanceOf(strategy.address)
    prevCvxCrvBalance = cvxCrv.balanceOf(strategy.address)
    prevCvxRwrdsBalance = cvx.balanceOf(strategy.cvxRewardsPool())
    prevCvxCrvRwrdsBalance = cvxCrv.balanceOf(strategy.cvxCrvRewardsPool())

    tx = strategy.tend({"from": stratKeeper})
    event = tx.events["TendState"][0]
    print("Tend Event:", event)

    # Check that cvxCrv and Cvx balances increase
    if event["cvxTended"] > 0:
        assert cvx.balanceOf(strategy.cvxRewardsPool()) > prevCvxRwrdsBalance
        assert prevCvxBalance == 0
        assert cvx.balanceOf(strategy.address) == 0

    if event["cvxCrvTended"] > 0:
        assert cvxCrv.balanceOf(strategy.cvxCrvRewardsPool()) > prevCvxCrvRwrdsBalance
        assert prevCvxCrvBalance == 0
        assert cvxCrv.balanceOf(strategy.address) == 0

    print_want_balances("After tend() is called 1st time")
    print_rewards_lp_balances("After tend() is called 1st time")

    chain.sleep(days(1))
    chain.mine()

    # Harvest
    strategy.harvest({"from": stratKeeper})

    print_want_balances("After harvest() is called")
    print_rewards_lp_balances("After harvest() is called")

    chain.sleep(days(1))
    chain.mine()

    # Tend 2
    prevCvxBalance = cvx.balanceOf(strategy.address)
    prevCvxCrvBalance = cvxCrv.balanceOf(strategy.address)
    prevCvxRwrdsBalance = cvx.balanceOf(strategy.cvxRewardsPool())
    prevCvxCrvRwrdsBalance = cvxCrv.balanceOf(strategy.cvxCrvRewardsPool())

    tx = strategy.tend({"from": stratKeeper})
    event = tx.events["TendState"][0]

    # Check that cvxCrv and Cvx balances increase
    if event["cvxTended"] > 0:
        assert cvx.balanceOf(strategy.cvxRewardsPool()) > prevCvxRwrdsBalance
        assert prevCvxBalance == 0
        assert cvx.balanceOf(strategy.address) == 0

    if event["cvxCrvTended"] > 0:
        assert cvxCrv.balanceOf(strategy.cvxCrvRewardsPool()) > prevCvxCrvRwrdsBalance
        assert prevCvxCrvBalance == 0
        assert cvxCrv.balanceOf(strategy.address) == 0

    print_want_balances("After tend() is called 2nd time")
    print_rewards_lp_balances("After tend() is called 2nd time")

    # Withdraw 1
    # Initial conditions
    startingBalanceVault = want.balanceOf(vault.address)
    startingBalanceStrat = want.balanceOf(strategy.address)
    startingBalanceOfPool = strategy.balanceOfPool()
    startingTotalSupply = vault.totalSupply()
    startingRewardsBalance = want.balanceOf(controller.rewards())

    vault.withdraw(depositAmount // 2, {"from": user1})

    # Want in the strategy should be decreased, if idle in sett is insufficient to cover withdrawal
    if (depositAmount // 2) > startingBalanceVault:
        # Adjust amount based on total balance x total supply
        # Division in python is not accurate, use Decimal package to ensure division is consistent
        # w/ division inside of EVM
        expectedWithdraw = Decimal(
            (depositAmount // 2) * startingBalanceVault
        ) / Decimal(startingTotalSupply)
        # Withdraw from idle in sett first
        expectedWithdraw -= startingBalanceVault
        # First we attempt to withdraw from idle want in strategy
        if expectedWithdraw > startingBalanceStrat:
            # If insufficient, we then attempt to withdraw from activities (balance of pool)
            # Just ensure that we have enough in the pool balance to satisfy the request
            expectedWithdraw -= startingBalanceStrat
            assert expectedWithdraw <= startingBalanceOfPool

            assert approx(
                startingBalanceOfPool,
                strategy.balanceOfPool() + expectedWithdraw,
                1,
            )

    # The total want between the strategy and sett should be less after than before
    # if there was previous want in strategy or sett (sometimes we withdraw entire
    # balance from the strategy pool) which we check above.
    if startingBalanceStrat > 0 or startingBalanceVault > 0:
        assert (want.balanceOf(strategy.address) + want.balanceOf(vault.address)) < (
            startingBalanceStrat + startingBalanceVault
        )

    # Controller rewards should earn
    if (
        strategy.withdrawalFee() > 0
        and
        # Fees are only processed when withdrawing from the strategy.
        startingBalanceStrat > want.balanceOf(strategy.address)
    ):
        assert want.balanceOf(controller.rewards()) > startingRewardsBalance

    # User1's shares decrease after withdraw
    assert vault.balanceOf(user1.address) < sharesUser1

    print_want_balances(
        "After user1 withdraws "
        + str((depositAmount // 2) / Wei("1 ether"))
        + " shares"
    )
    print_rewards_lp_balances(
        "After user1 withdraws "
        + str((depositAmount // 2) / Wei("1 ether"))
        + " shares"
    )

    print(
        "Fees Withdraw 1: ",
        (want.balanceOf(controller.rewards()) - startingRewardsBalance)
        / Wei("1 ether"),
    )

    # Withdraw 2
    # Initial conditions
    startingBalanceVault = want.balanceOf(vault.address)
    startingBalanceStrat = want.balanceOf(strategy.address)
    startingBalanceOfPool = strategy.balanceOfPool()
    startingTotalSupply = vault.totalSupply()
    startingRewardsBalance = want.balanceOf(controller.rewards())

    # User2 can't withdraw since they have no shares
    with brownie.reverts("ERC20: burn amount exceeds balance"):
        vault.withdraw(depositAmount, {"from": user2})

    # User1 transfers the rest of their shares balance to User2
    remainingAmount = vault.balanceOf(user1.address)
    vault.transfer(user2.address, remainingAmount, {"from": user1})
    assert vault.balanceOf(user1.address) == 0
    assert vault.balanceOf(user2.address) == remainingAmount

    # User2 withdraws using the shares received
    vault.withdraw(remainingAmount, {"from": user2})

    # Want in the strategy should be decreased, if idle in sett is insufficient to cover withdrawal
    if remainingAmount > startingBalanceVault:
        # Adjust amount based on total balance x total supply
        # Division in python is not accurate, use Decimal package to ensure division is consistent
        # w/ division inside of EVM
        expectedWithdraw = Decimal(remainingAmount * startingBalanceVault) / Decimal(
            startingTotalSupply
        )
        # Withdraw from idle in sett first
        expectedWithdraw -= startingBalanceVault
        # First we attempt to withdraw from idle want in strategy
        if expectedWithdraw > startingBalanceStrat:
            # If insufficient, we then attempt to withdraw from activities (balance of pool)
            # Just ensure that we have enough in the pool balance to satisfy the request
            expectedWithdraw -= startingBalanceStrat
            assert expectedWithdraw <= startingBalanceOfPool

            assert approx(
                startingBalanceOfPool,
                strategy.balanceOfPool() + expectedWithdraw,
                1,
            )

    # The total want between the strategy and sett should be less after than before
    # if there was previous want in strategy or sett (sometimes we withdraw entire
    # balance from the strategy pool) which we check above.
    if startingBalanceStrat > 0 or startingBalanceVault > 0:
        assert (want.balanceOf(strategy.address) + want.balanceOf(vault.address)) < (
            startingBalanceStrat + startingBalanceVault
        )

    # Controller rewards should earn
    if (
        strategy.withdrawalFee() > 0
        and
        # Fees are only processed when withdrawing from the strategy.
        startingBalanceStrat > want.balanceOf(strategy.address)
    ):
        assert want.balanceOf(controller.rewards()) > startingRewardsBalance

    # User2's shares should be 0
    assert vault.balanceOf(user2.address) == 0

    print_want_balances(
        "After user2 withdraws " + str(remainingAmount / Wei("1 ether")) + " shares"
    )

    print(
        "Fees Withdraw 2: ",
        (want.balanceOf(controller.rewards()) - startingRewardsBalance)
        / Wei("1 ether"),
    )

    # === End of Flow === #

    # assert False
