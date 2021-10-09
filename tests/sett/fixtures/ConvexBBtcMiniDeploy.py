from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import sett_config
from helpers.token_utils import distribute_from_whales
from brownie import *
from helpers.proxy_utils import deploy_proxy
from helpers.constants import AddressZero


class ConvexBBtcMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.convexBbtcCrv.params
        want = sett_config.native.convexBbtcCrv.params.want

        params.badgerTree = self.badger.badgerTree

        return (params, want)

    def post_vault_deploy_setup(self, deploy=True):
        if not deploy:
            return
        distribute_from_whales(self.deployer, 1, "bbtcCrv")

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
            self.strategy.setCrvCvxCrvSlippageToleranceBps(500, {"from": self.governance})

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

        if not (self.vault.controller() == self.strategy.controller()):
            # NB: Not all vaults are pauseable.
            try:
                if self.vault.paused():
                    self.vault.unpause({"from": self.governance})
            except exceptions.VirtualMachineError:
                pass
            # Change vault's conroller to match the strat's
            self.vault.setController(
                self.strategy.controller(), {"from": self.governance}
            )

        # Check that vault's and Strat's controller is the same
        assert self.vault.controller() == self.strategy.controller()

        # Check that want is the same for vault and strategy
        assert self.vault.token() == self.strategy.want()

        self.controller = interface.IController(self.vault.controller())

        # The timelock is th assigned governance address for the vault and strategy
        timelock = accounts.at("0x21CF9b77F88Adf8F8C98d7E33Fe601DC57bC0893", force=True)

        # Add strategy to controller for want
        # Controller already wired-up
        # self.controller.approveStrategy(
        #     self.strategy.want(), self.strategy.address, {"from": self.governance}
        # )
        # self.controller.setStrategy(
        #     self.strategy.want(), self.strategy.address, {"from": self.governance}
        # )

        # Add vault to controller for want
        # self.controller.setVault(self.vault.token(), self.vault.address, {"from": self.governance})

        assert self.controller.strategies(self.vault.token()) == self.strategy.address
        assert self.controller.vaults(self.strategy.want()) == self.vault.address

        # Upgrade strategy
        proxyAdmin = interface.IProxyAdmin("0x20Dce41Acca85E8222D6861Aa6D23B6C941777bF")
        timelock = accounts.at("0x21CF9b77F88Adf8F8C98d7E33Fe601DC57bC0893", force=True) # Owner

        proxyAdmin.upgrade(self.strategy.address, "0xead9c2499187e5627dc2f9f75ab74f439c34c6fb", {"from": timelock})

        self.strategy.patchPaths({"from": self.governance})
        self.strategy.setCrvCvxCrvSlippageToleranceBps(500, {"from": self.governance})
        

        if self.vault.guestList() != AddressZero:
            # Add actors to guestlist
            guestlist = VipCappedGuestListBbtcUpgradeable.at(self.vault.guestList())

            addresses = []
            for account in accounts:
                addresses.append(account.address)

            # Add actors addresses
            addresses.append(guestlist.owner())
            addresses.append(self.governance.address)
            addresses.append(self.strategist.address)
            addresses.append(self.keeper.address)
            addresses.append(self.guardian.address)
            addresses.append(self.deployer.address)

            invited = [True] * len(addresses)

            guestlist.setGuests(addresses, invited, {"from": self.deployer})

