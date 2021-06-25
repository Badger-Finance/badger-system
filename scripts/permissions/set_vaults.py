from helpers.time_utils import days
from ape_safe import ApeSafe
from brownie import *
from helpers.constants import *
from eth_abi import encode_abi
from helpers.constants import MaxUint256
from helpers.gnosis_safe import ApeSafeHelper
from config.badger_config import badger_config, digg_config, sett_config

from scripts.systems.badger_system import connect_badger
from helpers.console_utils import console


# gas_strategies.set_default_for_active_chain()

vaults_to_add = ["native.hbtcCrv", "native.pbtcCrv", "native.obtcCrv", "native.bbtcCrv"]
vaults_to_add = ["native.pbtcCrv", "native.obtcCrv", "native.bbtcCrv"]
# new_strategies = {
#     "native.renCrv": "0x8cbb86a7e0780a6fbefeec108f9b4b0aa8193e24",
#     "native.sbtcCrv": "0xaa9b716ccd717761f40479cd81f8e3a5a7b4cad7",
#     "native.tbtcCrv": "0x1ac31c470b90e366c70efc1ac28d5d7fa2f1dbe1",
# }

controller_id = "native"

"""
function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address[3] memory _wantConfig,
        uint256 _pid,
        uint256[3] memory _feeConfig
    ) public initializer whenNotPaused {
"""

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
    for key in vaults_to_add:
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
        badger.testMultisig = "0x55949f769d0af7453881435612561d109fff07b8"

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
            [params.want, badger.badgerTree.address, cvxVault, cvxCrvVault],
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
    for key, value in new_strategies.items():
        console.print(f"Initializing strat {key} ({value})")
        controller = badger.getController("native")

        print(controller.governance(), controller.strategist())
        assert controller.governance() == badger.governanceTimelock

        strategy = StrategyConvexLpOptimizer.at(value)

        console.print(
            {
                "want": strategy.want(),
                "strat": strategy,
                "chaintime": chain.time(),
                "executable_at": chain.time() + days(2.5),
            }
        )

        timelock_params = {
            "destination": controller.address,
            "signature": "approveStrategy(address,address)",
            "data": encode_abi(
                ["address", "address"], [strategy.want(), strategy.address]
            ),
            "expiration": chain.time() + days(2.5),
        }

        console.print("timelock_params", timelock_params)

        txFilename = badger.governance_queue_transaction(
            timelock_params["destination"],
            timelock_params["signature"],
            timelock_params["data"],
            timelock_params["expiration"],
        )

        chain.sleep(days(2.9))
        chain.mine()
        badger.governance_execute_transaction_from_params(
            timelock_params["destination"],
            timelock_params["signature"],
            timelock_params["data"],
            timelock_params["expiration"],
        )
        chain.sleep(days(0.5))
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
        assert strategy.controller() == controller
        assert controller.approvedStrategies(want, strategy) == True
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


def main():
    """
    Promote an experimental vault to official status
    """
    badger = connect_badger(load_deployer=True)

    if rpc.is_active():
        #     dev_multi = ApeSafe(badger.devMultisig.address)
        #     helper = ApeSafeHelper(badger, dev_multi)
        a = 1
    else:
        from helpers.gas_utils import gas_strategies

        gas_strategies.set_default(gas_strategies.exponentialScalingFast)

        # set_guest_lists(badger, dev_multi, helper, vaults_to_add)
    # set_strategies_on_controller(badger, dev_multi, helper, vaults_to_add)
    initialize_strategies(badger)

    # set_vaults_on_controller(badger, dev_multi, ApeSafeHelper(badger, dev_multi), vaults_to_add)
    # upgrade_vault_proxy_admins(badger, vaults_to_add)
    # initialize_strategies(badger)
    # approve_strategies(badger, dev_multi, helper)
    # config_guest_lists(badger)
    # unpause_vaults(badger, dev_multi, helper, vaults_to_add))

    # helper.publish()

    # set_controller_on_vaults(badger, dev_multi, ApeSafeHelper(badger,x dev_multi), vaults_to_add)

    # helper.publish()
