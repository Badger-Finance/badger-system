import json
from brownie import (
    web3,
    MStableVoterProxy,
)

from helpers.registry import registry, artifacts
from helpers.proxy_utils import deploy_proxy
from dotmap import DotMap

from rich.console import Console

console = Console()

class MStableSystem:
    """
    The mStable System consists of the MStableVoterProxy
    """

    def __init__(self, deployer, devProxyAdmin, config):
        self.deployer = deployer
        self.devProxyAdmin = devProxyAdmin
        self.config = config
        self.logic = DotMap()

    # ===== Deployers =====

    def deploy_voterproxy_proxy(self):
        config = self.config
        devProxyAdmin = self.devProxyAdmin
        deployer = self.deployer
        logic = self.logic
        self.voterproxy = deploy_proxy(
            "MStableVoterProxy",
            MStableVoterProxy.abi,
            logic.MStableVoterProxy.address,
            web3.toChecksumAddress(devProxyAdmin.address),
            logic.MStableVoterProxy.initialize.encode_input(
                config.dualGovernance.address,
                config.badgerGovernance.address,
                config.strategist.address,
                config.keeper.address,
                [
                    config.configAddress1,
                    config.configAddress2,
                ],
                [config.rates],
            ),
            deployer,
        )

    def deploy_logic(self, name, BrownieArtifact):
        deployer = self.deployer
        self.logic[name] = BrownieArtifact.deploy(
            {"from": deployer},
        )

