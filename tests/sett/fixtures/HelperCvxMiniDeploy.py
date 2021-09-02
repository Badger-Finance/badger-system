from helpers.constants import MaxUint256
from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import sett_config
from helpers.token_utils import distribute_from_whales
from brownie import *
from helpers.proxy_utils import deploy_proxy
from scripts.systems.constants import SettType
from helpers.constants import AddressZero


class HelperCvxMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.helper.cvx.params
        want = sett_config.helper.cvx.params.want

        return (params, want)

    def post_vault_deploy_setup(self, deploy=True):
        if deploy:
            distribute_from_whales(self.deployer, 1, "cvx")

    def post_deploy_setup(self, deploy):
        if deploy:
            return

        # Vault uses testMultisig
        self.testMultisig = accounts.at(self.vault.governance(), force=True)

        # NB: Not all vaults are pauseable.
        try:
            if self.vault.paused():
                self.vault.unpause({"from": self.testMultisig})
        except exceptions.VirtualMachineError:
            pass

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

        assert self.controller.strategies(self.vault.token()) == self.strategy.address
        assert self.controller.vaults(self.strategy.want()) == self.vault.address

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

            owner = accounts.at(guestlist.owner(), force=True)

            guestlist.setGuests(addresses, invited, {"from": owner})
            guestlist.setUserDepositCap(MaxUint256, {"from": owner})
            guestlist.setTotalDepositCap(MaxUint256, {"from": owner})
