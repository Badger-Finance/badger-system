from helpers.time_utils import days
from ape_safe import ApeSafe
from brownie import *
from helpers.constants import *
from eth_abi import encode_abi
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from config.badger_config import badger_config, digg_config, sett_config
from helpers.registry import artifacts
from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console
from helpers.registry import registry

# from helpers.gas_utils import gas_strategies
# gas_strategies.set_default(gas_strategies.exponentialScalingFast)
# gas_strategies.set_default_for_active_chain()

vaults_to_add = [
    "native.hbtcCrv",
    "native.pbtcCrv",
    "native.obtcCrv",
    "native.bbtcCrv",
    "native.tricrypto",
    "native.cvxCrv",
    "native.cvx",
]
new_core_vaults = [
    "native.hbtcCrv",
    "native.pbtcCrv",
    "native.obtcCrv",
    "native.bbtcCrv",
    "native.tricrypto",
]
helper_vaults = ["native.cvxCrv", "native.cvx"]
strategies_to_initialize = ["native.renCrv", "native.sbtcCrv", "native.tbtcCrv"]
controller_id = "experimental"

params = {
    "root": "0x17bf188285a653a6c0ccb51a826c35c9f948be7691836e486a1dae56740730cf",
    "user_deposit_cap": 2 * 10 ** 18,
    "total_deposit_cap": 60 * 10 ** 18,
}


def set_strategists(badger):
    """
    All strategists should be moved to a new keeper account. This will accumulate DAO strategy funds and use them to fund operations.
    """
    assert False


def keeper_refresh(badger):
    """
    All vaults should have their keeper set to earn() keeper account
    All strategies should have their keeper set to harvester() keeper account
    """


def config_guest_lists(badger):
    for key in vaults_to_add:
        guestList = badger.getGuestList(key)
        sett = badger.getSett(key)

        console.print(
            f"📝 [yellow]Configuring guest list[/yellow] [blue]{guestList.address}[/blue] for key {key}"
        )

        console.print(" [purple]Params[/purple]", params)

        guestList.initialize(sett, {"from": badger.deployer})
        guestList.setUserDepositCap(
            params["user_deposit_cap"], {"from": badger.deployer}
        )
        guestList.setTotalDepositCap(
            params["total_deposit_cap"], {"from": badger.deployer}
        )
        guestList.setGuestRoot(params["root"], {"from": badger.deployer})


def set_guest_lists(badger, safe, helper, vaults_to_add):
    for key in vaults_to_add:
        guestList = badger.getGuestList(key)
        sett = safe.contract(badger.getSett(key).address)

        console.print(
            f"Setting guest list [blue]{guestList.address}[/blue] on vault {key}"
        )
        assert guestList.wrapper() == sett

        sett.setGuestList(guestList)

        assert sett.guestList() == guestList
    helper.publish()


def initialize_strategies(badger):
    """
    Approve and set strategies on the controller
    """
    for key in strategies_to_initialize:
        console.print(f"Initializing strat {key})")
        # Deploy and initialize the strategy
        print("Find Params")
        if key == "native.renCrv":
            params = sett_config.native.convexRenCrv.params
            want = sett_config.native.convexRenCrv.params.want
        if key == "native.sbtcCrv":
            params = sett_config.native.convexSbtcCrv.params
            want = sett_config.native.convexSbtcCrv.params.want
        if key == "native.tbtcCrv":
            params = sett_config.native.convexTbtcCrv.params
            want = sett_config.native.convexTbtcCrv.params.want
        if key == "native.hbtcCrv":
            params = sett_config.native.convexHbtcCrv.params
            want = sett_config.native.convexHbtcCrv.params.want
        if key == "native.pbtcCrv":
            params = sett_config.native.convexPbtcCrv.params
            want = sett_config.native.convexPbtcCrv.params.want
        if key == "native.obtcCrv":
            params = sett_config.native.convexObtcCrv.params
            want = sett_config.native.convexObtcCrv.params.want
        if key == "native.bbtcCrv":
            params = sett_config.native.convexBbtcCrv.params
            want = sett_config.native.convexBbtcCrv.params.want

        print(params)

        cvxCrvVault = "0x2B5455aac8d64C14786c3a29858E43b5945819C0"
        cvxVault = "0x53c8e199eb2cb7c01543c137078a038937a68e40"

        badger.keeper = "0x73433896620E71f7b1C72405b8D2898e951Ca4d5"
        badger.guardian = "0x29F7F8896Fb913CF7f9949C623F896a154727919"

        """
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[4] memory _wantConfig,
        uint256 _pid,
        uint256[3] memory _feeConfig,
        CurvePoolConfig memory _curvePool
        """

        strategy = badger.getStrategy(key)
        print(strategy, strategy.getName())
        console.print(f"Admin: {badger.getProxyAdmin(strategy)}")
        console.print(f"༄ [green]Initializing Strategy with params[/green]", params)
        strategy.initialize(
            badger.testMultisig,
            badger.testMultisig,
            badger.getController("experimental"),
            badger.keeper,
            badger.guardian,
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
            {"from": badger.deployer},
        )

        vault = badger.getSett(key)

        assert vault.token() == strategy.want()


def upgrade_setts(badger, helper, admin, new_logic, setts):
    """
    Upgrade setts
    """
    for key in setts:
        console.print(f"Upgrading strat {key} to new logic at {new_logic}")

        admin = helper.contract_from_abi(
            admin.address, "ProxyAdmin", artifacts.open_zeppelin["ProxyAdmin"]["abi"]
        )
        vault = helper.contract_from_abi(
            badger.getSett(key).address, "SettV4", SettV4.abi
        )

        want = interface.IERC20(vault.token())
        old_logic = admin.getProxyImplementation(vault)

        old_state = {
            "version": vault.version(),
            "governance": vault.governance(),
            "balance": vault.balance(),
        }

        console.print(old_state)

        admin.upgrade(vault, new_logic)
        assert admin.getProxyImplementation(vault) == new_logic

        new_state = {
            "version": vault.version(),
            "governance": vault.governance(),
            "balance": vault.balance(),
        }

        console.print(new_state)

        # Ensure selected state values stay consistent across upgrade
        for key, old_value in old_state.items():
            new_value = new_state[key]
            assert new_value == old_value

    helper.publish()


def upgrade_strategies(badger, helper, admin, new_logic, strategies):
    """
    Upgrade strategies
    """
    for key in strategies:
        console.print(f"Upgrading strat {key} to new logic at {new_logic}")

        admin = helper.contract_from_abi(
            admin.address, "ProxyAdmin", artifacts.open_zeppelin["ProxyAdmin"]["abi"]
        )
        console.print(Controller)
        strategy = helper.contract_from_abi(
            badger.getStrategy(key).address,
            "StrategyConvexStakingOptimizer",
            StrategyConvexStakingOptimizer.abi,
        )
        vault = helper.contract_from_abi(badger.getSett(key).address, "Sett", Sett.abi)
        controller = helper.contract_from_abi(
            strategy.controller(), "Controller", Controller.abi
        )

        want = interface.IERC20(strategy.want())

        old_logic = admin.getProxyImplementation(strategy)

        old_state = {
            "name": strategy.getName(),
            "goverannce": strategy.governance(),
            "balanceOf": strategy.balanceOf(),
            "balanceOfPool": strategy.balanceOfPool(),
        }

        admin.upgrade(strategy, new_logic)

        new_state = {
            "name": strategy.getName(),
            "goverannce": strategy.governance(),
            "balanceOf": strategy.balanceOf(),
            "balanceOfPool": strategy.balanceOfPool(),
        }

        # Ensure selected state values stay consistent across upgrade
        for key, old_value in old_state.items():
            new_value = new_state[key]
            assert new_value == old_value

        # Extra Initialization Steps
        # strategy.initializeApprovals()
        # strategy.setAutoCompoundingBps(2000)
        # strategy.setAutoCompoundingPerformanceFeeGovernance(5000)

    helper.publish()


def set_strategy_fees(
    badger,
    helper,
    withdrawalFee,
    performanceFeeStrategist,
    performanceFeeGovernance,
    strategies,
):
    for key in strategies:
        console.print(
            f"Setting strategy fees on {key} to {withdrawalFee} / {performanceFeeStrategist} / {performanceFeeGovernance}"
        )

        strategy = helper.contract_from_abi(
            badger.getStrategy(key).address,
            "StrategyConvexStakingOptimizer",
            StrategyConvexStakingOptimizer.abi,
        )
        vault = helper.contract_from_abi(badger.getSett(key).address, "Sett", Sett.abi)
        controller = helper.contract_from_abi(
            strategy.controller(), "Controller", Controller.abi
        )
        want = interface.IERC20(strategy.want())

        old_state = {
            "withdrawalFee": strategy.withdrawalFee(),
            "performanceFeeStrategist": strategy.performanceFeeStrategist(),
            "performanceFeeGovernance": strategy.performanceFeeGovernance(),
        }

        if old_state["withdrawalFee"] != withdrawalFee:
            strategy.setWithdrawalFee(withdrawalFee)
        if old_state["performanceFeeStrategist"] != performanceFeeStrategist:
            strategy.setPerformanceFeeStrategist(performanceFeeStrategist)
        if old_state["performanceFeeGovernance"] != performanceFeeGovernance:
            strategy.setPerformanceFeeGovernance(performanceFeeGovernance)

        new_state = {
            "withdrawalFee": strategy.withdrawalFee(),
            "performanceFeeStrategist": strategy.performanceFeeStrategist(),
            "performanceFeeGovernance": strategy.performanceFeeGovernance(),
        }

        assert new_state["withdrawalFee"] == withdrawalFee
        assert new_state["performanceFeeStrategist"] == performanceFeeStrategist
        assert new_state["performanceFeeGovernance"] == performanceFeeGovernance

    helper.publish()


def approve_strategies(badger, safe, helper):
    """
    Approve and set strategies on the controller
    """
    for key in vaults_to_add:
        console.print(f"Initializing strat {key}")
        controller = safe.contract(badger.getController("experimental").address)

        strategy = badger.getStrategy(key)
        vault = badger.getSett(key)

        want = interface.IERC20(strategy.want())

        console.print(
            f"Approving strategy {strategy} for want {want.name()} {want.address}"
        )

        controller.approveStrategy(strategy.want(), strategy)
        controller.setStrategy(strategy.want(), strategy)

        assert controller.approvedStrategies(strategy.want(), strategy) == True
        assert controller.strategies(strategy.want()) == strategy
        assert controller.vaults(strategy.want()) == vault

    helper.publish()


def approve_strategies_timelock(badger):
    """
    Approve and set strategies on the controller
    """
    all_timelock_params = {}

    for key in strategies_to_initialize:
        strategy = badger.getStrategy(key)

        console.print(f"Initializing strat {key} ({strategy.address})")
        controller = badger.getController("native")

        print(controller.governance(), controller.strategist())
        assert controller.governance() == badger.governanceTimelock

        console.print(
            {
                "want": strategy.want(),
                "strat": strategy,
                "chaintime": chain.time(),
                "executable_at": chain.time() + days(2.5),
            }
        )

        timelock_params = {
            "target": controller.address,
            "signature": "approveStrategy(address,address)",
            "data": encode_abi(
                ["address", "address"], [strategy.want(), strategy.address]
            ),
            "eta": chain.time() + days(2.9),
        }

        all_timelock_params[key] = timelock_params

        console.print("timelock_params", timelock_params)

        txFilename = badger.governance_queue_transaction(
            timelock_params["target"],
            timelock_params["signature"],
            timelock_params["data"],
            timelock_params["eta"],
        )

    chain.sleep(days(3.5))
    chain.mine()

    for key in strategies_to_initialize:
        strategy = badger.getStrategy(key)
        timelock_params = all_timelock_params[key]

        badger.governance_execute_transaction_from_params(timelock_params)

        chain.mine()

        console.print(
            f"Checking strategy approval for {strategy.want()} {strategy} {controller.approvedStrategies(strategy.want(), strategy)}"
        )
        assert controller.approvedStrategies(strategy.want(), strategy) == True


def upgrade_vault_proxy_admins(badger, vaults_to_add):
    for settID in vaults_to_add:
        sett = badger.getSett(settID)
        console.print(f"Sett {settID} admin is [green]{badger.getProxyAdmin(sett)}")
        badger.testProxyAdmin.changeProxyAdmin(
            sett, badger.opsProxyAdmin, {"from": badger.deployer}
        )
        console.print(
            f"    Changed {settID} admin -> [blue]{badger.getProxyAdmin(sett)}"
        )


def set_controller_on_vaults(badger, safe, helper, vaults_to_add):
    for settID in vaults_to_add:
        sett = safe.contract(badger.getSett(settID).address)
        token = interface.IERC20(sett.token())
        controller = badger.getController(controller_id)

        sett.unpause()
        sett.setController(controller)
        sett.pause()

        print(badger.getProxyAdmin(sett))


def unpause_vaults(badger, safe, helper, vaults_to_add):
    for key in vaults_to_add:
        console.print(f"Unpause Vaults {key}")
        controller = safe.contract(badger.getController("experimental").address)

        vault = safe.contract(badger.getSett(key).address)
        strategy = badger.getStrategy(key)
        assert strategy.paused() == False

        console.print(
            {
                "vault_gov": vault.governance(),
                "strat_gov": strategy.governance(),
            }
        )

        vault.unpause()

        assert vault.paused() == False


def allow_strategies_on_rewards_manager(badger, safe, helper, vaults_to_add):
    earner = "0x46099Ffa86aAeC689D11F5D5130044Ff7082C2AD"
    keeper = "0x73433896620E71f7b1C72405b8D2898e951Ca4d5"
    external_harvester = "0x64E2286148Fbeba8BEb4613Ede74bAc7646B2A2B"

    for key in vaults_to_add:
        console.print(f"Keeper Tuneup {key}")
        controller = safe.contract(badger.getController("experimental").address)
        sett = safe.contract(badger.getSett(key).address)

        if sett.controller() != controller:
            print(
                f"Sett controller is {sett.controller()} rather than {controller.address}"
            )
            continue

        strategy = safe.contract(badger.getSett(key).address)
        rm = safe.contract(badger.badgerRewardsManager.address)

        # Set all Sett keepers to RM
        if sett.keeper() != rm:
            console.print(f"Sett {key} keeper -> {rm.address}")
            sett.setKeeper(rm)

        # Set all Strategy keepers to RM
        if strategy.keeper() != rm:
            console.print(f"Strategy {key} keeper -> {rm.address}")
            strategy.setKeeper(rm)

    helper.publish()


def allow_strategies_on_rewards_manager(badger, safe, helper, vaults_to_add):
    earner = "0x46099Ffa86aAeC689D11F5D5130044Ff7082C2AD"
    keeper = "0x73433896620E71f7b1C72405b8D2898e951Ca4d5"
    external_harvester = "0x64E2286148Fbeba8BEb4613Ede74bAc7646B2A2B"

    for key in vaults_to_add:
        console.print(f"Allow Strat {key} on Rewards Manager")
        controller = safe.contract(badger.getController("experimental").address)
        sett = safe.contract(badger.getSett(key).address)

        if sett.controller() != controller:
            print(
                f"Sett controller is {sett.controller()} rather than {controller.address}"
            )
            continue

        strategy = safe.contract(badger.getSett(key).address)
        rm = safe.contract(badger.badgerRewardsManager.address)

        # Allow any setts that are not approved
        if not rm.hasRole(APPROVED_SETT_ROLE, sett):
            console.print(f"[blue]Sett {key} as APPROVED_SETT[/blue]")
            rm.grantRole(APPROVED_SETT_ROLE, sett)
            assert rm.hasRole(APPROVED_SETT_ROLE, sett)

        # Allow any strategies that are not approved
        if not rm.isApprovedStrategy(strategy):
            console.print(f"[blue]Strategy {key} as APPROVED_STRATEGY[/blue]")
            rm.approveStrategy(strategy)
            assert rm.isApprovedStrategy(strategy)

    # Approve new earner & keeper
    console.print(f"[blue]New earner {earner} EARNER[/blue]")
    rm.grantRole(EARNER_ROLE, earner)

    console.print(f"[blue]New keeper {keeper} KEEPER[/blue]")
    rm.grantRole(KEEPER_ROLE, keeper)

    # Revoke old keeper
    # rm.revokeRole(KEEPER_ROLE, badger.keeper)
    # rm.revokeRole(SWAPPER_ROLE, badger.keeper)
    # rm.revokeRole(DISTRIBUTOR_ROLE, badger.keeper)

    console.print(
        f"[blue]External harvester {external_harvester} as SWAPPER + DISTRIBUTOR[/blue]"
    )
    rm.grantRole(SWAPPER_ROLE, external_harvester)
    rm.grantRole(DISTRIBUTOR_ROLE, external_harvester)

    helper.publish()


def modify_curve_swap_addresses(badger, helper):
    strategy_address = badger.getStrategy("native.pbtcCrv").address
    strategy = helper.contract_from_abi(
        strategy_address,
        "StrategyConvexStakingOptimizer",
        StrategyConvexStakingOptimizer.abi,
    )
    strategy.setCurvePoolSwap(registry.curve.pools.pbtcCrv.swap)

    strategy_address = badger.getStrategy("native.obtcCrv").address
    strategy = helper.contract_from_abi(
        strategy_address,
        "StrategyConvexStakingOptimizer",
        StrategyConvexStakingOptimizer.abi,
    )
    strategy.setCurvePoolSwap(registry.curve.pools.obtcCrv.swap)

    strategy_address = badger.getStrategy("native.bbtcCrv").address
    strategy = helper.contract_from_abi(
        strategy_address,
        "StrategyConvexStakingOptimizer",
        StrategyConvexStakingOptimizer.abi,
    )
    strategy.setCurvePoolSwap(registry.curve.pools.bbtcCrv.swap)
    helper.publish()


def set_withdrawal_fee(badger, safe, helper, vaults_to_add):
    vaults_to_add = ["experimental.sushiIBbtcWbtc"]
    for key in vaults_to_add:
        console.print(f"Reduce Fees on Strats {key}")
        controller = safe.contract(badger.getController("experimental").address)

        # vault = safe.contract(badger.getSett(key).address)
        assert strategy.withdrawalFee() == 50
        strategy = safe.contract(badger.getStrategy(key).address)
        assert strategy.paused() == False

        console.print(
            {
                "strat_gov": strategy.governance(),
            }
        )

        strategy.setWithdrawalFee(20)
        assert strategy.withdrawalFee() == 20
    helper.publish()


def set_strategies_on_controller(badger, safe, helper, vaults_to_add):
    controller_id = "experimental"
    for key in vaults_to_add:

        controller = safe.contract(badger.getController(controller_id).address)

        vault = safe.contract(badger.getSett(key).address)
        strategy = safe.contract(badger.getStrategy(key).address)

        console.print(
            f"Approve & Set strategy {strategy.address} ({strategy.getName()}) for {key} controller {controller_id}"
        )

        want = interface.IERC20(strategy.want())

        controller.approveStrategy(want, strategy)
        controller.setStrategy(want, strategy)

        assert vault.controller() == controller
        # assert strategy.controller() == controller
        # print(controller.approvedStrategies(want, strategy))
        # assert controller.approvedStrategies(want, strategy) == True
        assert controller.strategies(want) == strategy.address
        assert vault.paused() == False
        assert strategy.paused() == False

    helper.publish()


def set_vaults_on_controller(badger, safe, helper, vaults_to_add):
    for settID in vaults_to_add:
        sett = safe.contract(badger.getSett(settID).address)
        token = interface.IERC20(sett.token())
        console.print(f"Sett controller is [yellow]{sett.controller()}[/yellow]")
        controller = safe.contract(badger.getController(controller_id).address)
        console.print(
            f"Vault for token [green]{token.name()}[/green] ({token.address}) on controller [yellow]{controller.address}[/yellow] set to [green] {settID} [blue]{sett.address}[/blue]"
        )
        controller.setVault(sett.token(), sett)
    helper.publish()


def update_rm(badger, safe, helper):
    rm = safe.contract(badger.badgerRewardsManager.address)
    opsAdmin = safe.contract(badger.opsProxyAdmin.address)

    logic = badger.getLogic("BadgerRewardsManager")

    console.print(f"Updating RM at {rm.address} to logic {logic}")

    opsAdmin.upgrade(rm, logic)

    assert rm.getRoleMember(DEFAULT_ADMIN_ROLE, 0) == badger.devMultisig
    helper.publish()


def main():
    """
    Promote an experimental vault to official status
    """
    badger = connect_badger(load_deployer=True)

    if rpc.is_active():
        dev_multi = ApeSafe(badger.testMultisig.address)
        helper = ApeSafeHelper(badger, dev_multi)
    else:
        from helpers.gas_utils import gas_strategies

        gas_strategies.set_default(gas_strategies.exponentialScalingFast)

    # set_guest_lists(badger, dev_multi, helper, vaults_to_add)
    # set_withdrawal_fee(badger, dev_multi, helper, vaults_to_add)
    # initialize_strategies(badger)

    # allow_strategies_on_rewards_manager(badger, dev_multi, helper, vaults_to_add)
    # update_rm(badger, dev_multi, helper)
    # set_vaults_on_controller(badger, dev_multi, helper, vaults_to_add)
    # set_strategies_on_controller(badger, dev_multi, helper, vaults_to_add)

    # set_strategy_fees(badger, dev_multi, helper, helper_vaults)
    # approve_strategies_timelock(badger)
    # initialize_strategies(badger)
    # set_strategy_fees(badger, helper, 20, 0, 2000, new_core_vaults)
    # upgrade_strategies(badger, helper, badger.testProxyAdmin, "0x8cea9A8360f78dE508E01C6B082279Fe34c75f77", ['native.cvxCrv'])
    # upgrade_strategies(badger, dev_multi, helper, badger.testProxyAdmin, "0xBabAE0E133cd5a6836a63820284cCD8B14D9272a", new_core_vaults)
    # modify_curve_swap_addresses(badger, helper)
    strategy = helper.contract_from_abi(
        badger.getStrategy("native.cvxCrv").address,
        "StrategyCvxCrvHelper",
        StrategyCvxCrvHelper.abi,
    )
    strategy.setCrvCvxCrvPath()

    helper.publish()

    # upgrade_vault_proxy_admins(badger, vaults_to_add)
    # initialize_strategies(badger)
    # approve_strategies(badger, dev_multi, helper)
    # config_guest_lists(badger)
    # unpause_vaults(badger, dev_multi, helper, vaults_to_add))

    # helper.publish()

    # set_controller_on_vaults(badger, dev_multi, helper, vaults_to_add)

    # helper.publish()
