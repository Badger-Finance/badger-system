from ape_safe import ApeSafe
from helpers.gnosis_safe import GnosisSafe
from helpers.token_utils import distribute_test_ether
from scripts.systems.constants import SettType
from scripts.systems.badger_system import BadgerSystem, connect_badger
from config.badger_config import badger_config, sett_config, digg_config
from brownie import *
import json

class DiggStabilizeMiniDeploy:
    def deploy(self, sett_type=SettType.DEFAULT, deploy=True) -> BadgerSystem:
        badger = connect_badger()

        digg = badger.digg
        dev = badger.deployer

        timelock = badger.digg.daoDiggTimelock

        multi = GnosisSafe(badger.devMultisig)
        safe = ApeSafe(badger.devMultisig.address)
        ops = ApeSafe(badger.opsMultisig.address)

        # controller = ops.contract(badger.getController("experimental").address)
        controller = Controller.at(badger.getController("experimental").address)

        # devMultisig
        governance = accounts.at(controller.governance(), force=True)

        stabilizeVault = "0xE05D2A6b97dce9B8e59ad074c2E4b6D51a24aAe3"
        diggTreasury = DiggTreasury.deploy({"from": dev})

        strategy = StabilizeStrategyDiggV1.deploy({"from": dev})
        strategy.initialize(
            governance.address,
            dev,
            controller,
            badger.keeper,
            badger.guardian,
            0,
            [stabilizeVault, diggTreasury],
            [250, 0, 50, 250],
            {"from": dev},
        )

        diggTreasury.initialize(strategy, {"from": dev})

        """
            address _governance,
            address _strategist,
            address _controller,
            address _keeper,
            address _guardian,
            uint256 _lockedUntil,
            address[2] memory _vaultConfig,
            uint256[4] memory _feeConfig
        """

        with open(digg_config.prod_json) as f:
            badger_deploy = json.load(f)

        vault = StabilizeDiggSett.at(
            badger_deploy["sett_system"]["vaults"]["experimental.digg"]
        )

        # Used to deploy vault locally:

        # vault = StabilizeDiggSett.deploy({"from": dev})
        # vault.initialize(
        #     digg.token,
        #     controller,
        #     governance.address,
        #     badger.keeper,
        #     badger.guardian,
        #     False,
        #     "",
        #     "",
        # ),

        print("governance", controller.governance())

        controller.approveStrategy(digg.token, strategy.address, {"from": governance})
        controller.setStrategy(digg.token, strategy.address, {"from": governance})
        # controller.setVault(digg.token, vault.address, {"from": governance})

        badger.controller = controller
        badger.strategy = strategy
        badger.vault = vault

        assert controller.strategies(vault.token()) == strategy.address
        assert controller.vaults(strategy.want()) == vault.address
        
        self.badger = badger
        return self.badger
