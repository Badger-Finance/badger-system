from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import sett_config, digg_config
from helpers.token_utils import distribute_from_whales
from brownie import *
from helpers.proxy_utils import deploy_proxy
from helpers.registry import registry
from helpers.constants import AddressZero
import json


class ConvexOBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.convexObtcCrv.params
        want = sett_config.native.convexObtcCrv.params.want

        params.badgerTree = self.badger.badgerTree

        return (params, want)

    def post_vault_deploy_setup(self, deploy=True):
        if not deploy:
            return
        distribute_from_whales(self.deployer, 1, "obtcCrv")

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

            # self.strategy.patchPaths({"from": self.governance})
            # self.strategy.setCrvCvxCrvSlippageToleranceBps(500, {"from": self.governance})

            if (cvxHelperVault.guestList() != AddressZero) and (
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

                 # ====== Strategy Migration Implementations ====== #
        with open(digg_config.prod_json) as f:
            badger_deploy = json.load(f)

        # Fetch strategy from strategy_registry
        self.strategy = StrategyConvexStakingOptimizer.at(
            badger_deploy["sett_system"]["strategies_registry"]["native.obtcCrv"][
                "StrategyConvexStakingOptimizer"
            ]
        )
        self.badger.sett_system.strategies[self.key] = self.strategy
        print("Old Strategy:", self.strategy.address)

        if not (self.vault.controller() == self.strategy.controller()):
            # Change vault's controller to match the strat's
            self.vault.setController(
                self.strategy.controller(), {"from": self.governance}
            )

        # Check that vault's and Strat's controller is the same
        assert self.vault.controller() == self.strategy.controller()

        # Check that want is the same for vault and strategy
        assert self.vault.token() == self.strategy.want()

        self.controller = interface.IController(self.vault.controller())

        assert self.controller.strategies(self.vault.token()) == self.strategy.address
        assert self.controller.vaults(self.strategy.want()) == self.vault.address

        # Migrate strategy
        # ==== Pre-Migration checks ==== #
        # Balance of Sett (Balance on Sett, Controller and Strategy) is greater than 0
        initialSettBalance = self.vault.balance()
        assert initialSettBalance > 0
        # PPFS before migration
        ppfs = self.vault.getPricePerFullShare()

        controllerGov = accounts.at(self.controller.governance(), force=True)
        newStrategy = badger_deploy["sett_system"]["strategies_registry"]["native.obtcCrv"][
                "StrategyConvexStakingOptimizerV1.1"
            ]
        self.controller.approveStrategy(
            self.strategy.want(), newStrategy, {"from": controllerGov}
        )
        self.controller.setStrategy(
            self.strategy.want(), newStrategy, {"from": controllerGov}
        )
        assert self.controller.strategies(self.vault.token()) == newStrategy
        # Balance of old Strategy goes down to 0
        assert self.strategy.balanceOf() == 0

        self.strategy = StrategyConvexStakingOptimizer.at(newStrategy)
        self.badger.sett_system.strategies[self.key] = self.strategy

        # ==== Post-Migration checks ==== #
        # Balance of Sett remains the same
        assert initialSettBalance == self.vault.balance()

        # Balance of new Strategy starts off at 0
        assert self.strategy.balanceOf() == 0
        # PPS remain the same post migration
        assert ppfs == self.vault.getPricePerFullShare()

        stratGov = accounts.at(self.strategy.governance(), force=True)

        self.strategy.setController(self.controller.address, {"from": stratGov})
        assert self.vault.controller() == self.strategy.controller()
        
        self.strategy.setGovernance(self.governance.address, {"from": stratGov})

        self.keeper = accounts.at(self.strategy.keeper(), force=True)
        self.guardian = accounts.at(self.strategy.guardian(), force=True)
        self.strategist = accounts.at(self.strategy.strategist(), force=True)

        # Run Earn()
        self.vault.earn({"from": self.governance})

        # Approve strategy to interact with Helper Vaults:
        (params, want) = self.fetch_params()

        cvxHelperVault = SettV4.at(params.cvxHelperVault)
        cvxCrvHelperVault = SettV4.at(params.cvxCrvHelperVault)

        cvxHelperGov = accounts.at(cvxHelperVault.governance(), force=True)
        cvxCrvHelperGov = accounts.at(cvxCrvHelperVault.governance(), force=True)

        cvxHelperVault.approveContractAccess(
            self.strategy.address, {"from": cvxHelperGov}
        )
        cvxCrvHelperVault.approveContractAccess(
            self.strategy.address, {"from": cvxCrvHelperGov}
        )

        print("Vault:", self.vault.address)
        print("Controller:", self.controller.address)
        print("New Strategy:", self.strategy.address)
        print("Governance:", self.governance.address)

