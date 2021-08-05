from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config, digg_config
from helpers.registry import registry
from helpers.token_utils import distribute_from_whales
from brownie import *
from helpers.proxy_utils import deploy_proxy
import json
from helpers.constants import AddressZero


class ConvexTriCryptoDosMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.native.convexTriCryptoDos.params
        want = sett_config.native.convexTriCryptoDos.params.want

        params.badgerTree = self.badger.badgerTree

        return (params, want)

    def post_vault_deploy_setup(self, deploy=True):
        if not deploy:
            return
        whale = accounts.at("0xDeFd8FdD20e0f34115C7018CCfb655796F6B2168", force=True)
        token = interface.IERC20(sett_config.native.convexTriCryptoDos.params.want)
        balance = token.balanceOf(whale)
        token.transfer(self.deployer, balance // 2, {"from": whale})

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

            # Add rewards address to guestlists
            list_add = cvxHelperVault.guestList()
            if list_add != AddressZero:
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

        # Vault uses testMultisig
        testMultisig = accounts.at(self.vault.governance(), force=True)

        if not (self.vault.controller() == self.strategy.controller()):
            # NB: Not all vaults are pauseable.
            try:
                if self.vault.paused():
                    self.vault.unpause({"from": self.testMultisig})
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
        self.controller.approveStrategy(
            self.strategy.want(), self.strategy.address, {"from": self.governance}
        )
        self.controller.setStrategy(
            self.strategy.want(), self.strategy.address, {"from": self.governance}
        )

        assert self.controller.strategies(self.vault.token()) == self.strategy.address
        assert self.controller.vaults(self.strategy.want()) == self.vault.address

        # Add users to guestlist
        guestlist = VipCappedGuestListBbtcUpgradeable.at(self.vault.guestList())

        owner = accounts.at("0xd41f7006bcb2B3d0F9C5873272Ebed67B37F80Dc", force=True)

        addresses = []
        for account in accounts:
            addresses.append(account.address)

        # Add actors addresses
        addresses.append(owner.address)
        addresses.append(self.governance.address)
        addresses.append(self.strategist.address)
        addresses.append(self.keeper.address)
        addresses.append(self.guardian.address)
        addresses.append(self.deployer.address)

        invited = [True] * len(addresses)

        guestlist.setGuests(addresses, invited, {"from": owner})

        # Increase gustlist caps since randomly generated amounts tend to be bigger than current caps
        guestlist.setTotalDepositCap("5080189446897250400000", {"from": owner})
        guestlist.setUserDepositCap("5081890446897250400000", {"from": owner})

    # Setup used for running simulation without deployed strategy:

    # def post_deploy_setup(self, deploy):
    #     if deploy:
    #         return

    #     (params, want) = self.fetch_params()

    #     self.controller = interface.IController(self.vault.controller())

    #     contract = StrategyConvexStakingOptimizer.deploy({"from": self.deployer})
    #     self.strategy = deploy_proxy(
    #         "StrategyConvexStakingOptimizer",
    #         StrategyConvexStakingOptimizer.abi,
    #         contract.address,
    #         web3.toChecksumAddress(self.badger.devProxyAdmin.address),
    #         contract.initialize.encode_input(
    #             self.governance.address,
    #             self.strategist.address,
    #             self.controller.address,
    #             self.keeper.address,
    #             self.guardian.address,
    #             [params.want, self.badger.badgerTree,],
    #             params.pid,
    #             [
    #                 params.performanceFeeGovernance,
    #                 params.performanceFeeStrategist,
    #                 params.withdrawalFee,
    #             ],
    #         ),
    #         self.deployer,
    #     )

    #     self.badger.sett_system.strategies[self.key] = self.strategy

    #     assert self.controller.address == self.strategy.controller()

    #     self.controller.approveStrategy(self.strategy.want(), self.strategy.address, {"from": self.governance})
    #     self.controller.setStrategy(self.strategy.want(), self.strategy.address, {"from": self.governance})

    #     assert self.controller.strategies(self.vault.token()) == self.strategy.address
