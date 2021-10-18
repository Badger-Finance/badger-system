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
            self.strategy.patchPaths({"from": self.governance})
            self.strategy.setCrvCvxCrvSlippageToleranceBps(500, {"from": self.governance})
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
        # Already wire-up
        # self.controller.approveStrategy(
        #     self.strategy.want(), self.strategy.address, {"from": self.governance}
        # )
        # self.controller.setStrategy(
        #     self.strategy.want(), self.strategy.address, {"from": self.governance}
        # )

        assert self.controller.strategies(self.vault.token()) == self.strategy.address
        assert self.controller.vaults(self.strategy.want()) == self.vault.address

        # Upgrade strategy
        proxyAdmin = interface.IProxyAdmin("0x20Dce41Acca85E8222D6861Aa6D23B6C941777bF")
        timelock = accounts.at("0x21CF9b77F88Adf8F8C98d7E33Fe601DC57bC0893", force=True) # Owner

        proxyAdmin.upgrade(self.strategy.address, "0x0281B0E6d94f8f04a0E6af8a901E018542bdCDb6", {"from": timelock})

        self.strategy.patchPaths({"from": self.governance})
        self.strategy.setCrvCvxCrvSlippageToleranceBps(500, {"from": self.governance})
        
        

        if (self.vault.guestList() != AddressZero):
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
