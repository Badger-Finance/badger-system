from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config, digg_config
from helpers.registry import registry
from helpers.token_utils import distribute_from_whales
from brownie import *
from helpers.proxy_utils import deploy_proxy
import json
from helpers.constants import AddressZero


class ConvexRenBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.convexRenCrv.params
        want = sett_config.native.convexRenCrv.params.want

        params.badgerTree = self.badger.badgerTree

        return (params, want)

    def post_vault_deploy_setup(self, deploy=True):
        if not deploy:
            return
        distribute_from_whales(self.deployer, 1, "renCrv")

    def post_deploy_setup(self, deploy):
        if deploy:
            # Approve strategy to interact with Helper Vaults:
            cvxHelperVault = SettV4.at(self.params.cvxHelperVault)
            cvxCrvHelperVault = SettV4.at(self.params.cvxCrvHelperVault)

            cvxHelperGov = accounts.at(cvxHelperVault.governance(), force=True)
            cvxCrvHelperGov = accounts.at(cvxCrvHelperVault.governance(), force=True)

            cvxHelperVault.approveContractAccess(
                self.strategy.address, {"from": cvxHelperGov}
            )
            cvxCrvHelperVault.approveContractAccess(
                self.strategy.address, {"from": cvxCrvHelperGov}
            )

            self.strategy.patchPaths({"from": self.governance})

            if (
                cvxHelperVault.guestList() != AddressZero
                ) and (
                cvxCrvHelperVault.guestList() != AddressZero
            ):

                # Add rewards address to guestlists
                cvxGuestlist = VipCappedGuestListBbtcUpgradeable.at(
                    cvxHelperVault.guestList()
                )
                cvxCrvGuestlist = VipCappedGuestListBbtcUpgradeable.at(
                    cvxCrvHelperVault.guestList()
                )

                cvxOwner = accounts.at(cvxGuestlist.owner(), force=True)
                cvxCrvOwner = accounts.at(cvxCrvGuestlist.owner(), force=True)

                cvxGuestlist.setGuests(
                    [self.controller.rewards(), self.strategy],
                    [True, True],
                    {"from": cvxOwner},
                )
                cvxCrvGuestlist.setGuests(
                    [self.controller.rewards(), self.strategy],
                    [True, True],
                    {"from": cvxCrvOwner},
                )  # Strategy added since SettV4.sol currently checks for the sender
                # instead of receipient for authorization on depositFor()

            return

        with open(digg_config.prod_json) as f:
            badger_deploy = json.load(f)

        # Fetch strategy from strategy_registry
        self.strategy = StrategyConvexStakingOptimizer.at(
            badger_deploy["sett_system"]["strategies_registry"]["native.renCrv"][
                "StrategyConvexStakingOptimizer"
            ]
        )
        self.badger.sett_system.strategies[self.key] = self.strategy

        if not (self.vault.controller() == self.strategy.controller()):
            # Change vault's conroller to match the strat's
            self.vault.setController(
                self.strategy.controller(), {"from": self.governance}
            )

        # Check that vault's and Strat's controller is the same
        assert self.vault.controller() == self.strategy.controller()

        # Check that want is the same for vault and strategy
        assert self.vault.token() == self.strategy.want()

        self.controller = interface.IController(self.vault.controller())

        # Add strategy to controller for want
        self.controller.approveStrategy(
            self.strategy.want(), self.strategy.address, {"from": self.governance}
        )
        self.controller.setStrategy(
            self.strategy.want(), self.strategy.address, {"from": self.governance}
        )
        self.controller.setVault(
            self.strategy.want(), self.vault.address, {"from": self.governance}
        )

        assert self.controller.strategies(self.vault.token()) == self.strategy.address
        assert self.controller.vaults(self.strategy.want()) == self.vault.address
