from ape_safe import ApeSafe
from helpers.gnosis_safe import GnosisSafe
from helpers.token_utils import distribute_test_ether
from scripts.systems.constants import SettType
from scripts.systems.badger_system import BadgerSystem, connect_badger
from config.badger_config import badger_config, sett_config
from brownie import *

class DiggStabilizeMiniDeploy():
    def deploy(self, sett_type=SettType.DEFAULT, deploy=True) -> BadgerSystem:
        badger = connect_badger()

        digg = badger.digg
        dev = badger.deployer

        timelock = badger.digg.daoDiggTimelock

        multi = GnosisSafe(badger.devMultisig)
        safe = ApeSafe(badger.devMultisig.address)
        ops = ApeSafe(badger.opsMultisig.address)

        bDigg = safe.contract_from_abi(badger.getSett("native.digg").address, "Sett", Sett.abi)
        
        controller = ops.contract(badger.getController("experimental").address)

        stabilizeVault = "0xE05D2A6b97dce9B8e59ad074c2E4b6D51a24aAe3"
        diggTreasury = DiggTreasury.deploy({"from": dev})
        
        strategy = StabilizeStrategyDiggV1.deploy({"from": dev})
        strategy.initialize(
            badger.devMultisig,
            dev,
            controller,
            badger.keeper,
            badger.guardian,
            0,
            [stabilizeVault, diggTreasury],
            [250, 0, 50, 250],
            {'from': dev}
        )

        diggTreasury.initialize(strategy, {'from': dev})

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

        print("governance", controller.governance())
        controller.approveStrategy(digg.token, strategy)
        controller.setStrategy(digg.token, strategy)
        self.badger = badger
        return self.badger