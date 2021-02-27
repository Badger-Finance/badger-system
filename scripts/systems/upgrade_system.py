from brownie import BrownieArtifact
from typing import Optional

from scripts.deploy.upgrade import upgrade_versioned_proxy
from .constants import (
    SETT_SUFFIX,
    STRATEGY_SUFFIX,
)


class UpgradeSystem:
    def __init__(self, badger, deployer):
        self.badger = badger
        self.deployer = deployer
        # NB: Currently the only versioned contracts are strategy/sett contracts.
        self.contracts_upgradeable = {}

    def upgrade_sett_contract(self, contractKey: str) -> None:
        self._upgrade_with_suffix(
            SETT_SUFFIX,
            self.badger.getSettArtifact,
            contractKey=contractKey,
        )

    def upgrade_strategy_contract(self, contractKey: str) -> None:
        self._upgrade_with_suffix(
            STRATEGY_SUFFIX,
            self.badger.getStrategyArtifact,
            contractKey=contractKey,
        )

    def upgrade_sett_contracts(self) -> None:
        self._upgrade_with_suffix(SETT_SUFFIX, self.badger.getSettArtifact)

    def upgrade_strategy_contracts(self) -> None:
        self._upgrade_with_suffix(STRATEGY_SUFFIX, self.badger.getStrategyArtifact)

    def _upgrade_contract(
            self,
            suffix: str,
            getArtifactFn: lambda str: BrownieArtifact,
            contractKey: Optional[str] = None,
    ) -> None:
        for key, contract in self.contracts_upgradeable.items():
            # If a contract key is specified, only attempt to upgrade that contract.
            if contractKey is not None and contractKey != key:
                continue

            if key.endswith(suffix):
                Artifact = getArtifactFn(key.removesuffix(suffix))
                latest = Artifact.deploy({"from": self.deployer})
                upgrade_versioned_proxy(
                    self.badger,
                    contract,
                    latest,
                )

    def track_contract_upgradeable(self, key, contract) -> None:
        self.contracts_upgradeable[key] = contract
