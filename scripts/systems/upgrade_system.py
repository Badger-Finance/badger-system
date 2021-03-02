from brownie import (
        DiggSett,
        Sett_A,
        Sett_B,
        exceptions,
)
from brownie.network.contract import ProjectContract
from typing import Optional, List, Tuple, Any
from rich.console import Console

from scripts.deploy.upgrade import upgrade_versioned_proxy
from .constants import (
    SETT_SUFFIX,
    STRATEGY_SUFFIX,
)

console = Console()

SETT_VALIDATION_FIELDS = [
    "token",
    "min",
    "max",
    "controller",
    "guardian",
]

# NB: These validation fields are generic to all strategies and will not cover all state vars
# in all strategies as some may inherit from other base contracts (e.g. BaseStrategyMultiSwapper).
# However, checking these should give us some base level of confidence in the upgrade.
STRATEGY_VALIDATION_FIELDS = [
    "want",
    "performanceFeeGovernance",
    "performanceFeeStrategist",
    "withdrawalFee",
    "MAX_FEE",
    "uniswap",
    "controller",
    "guardian",
]

# Track forked sett upgrade paths.
SETT_A = (
   "native.badger",
   "native.renCrv",
   "native.sbtcCrv",
   "native.tbtcCrv",
   "native.uniBadgerWbtc",
   "harvest.renCrv",
)

SETT_B = (
    "native.sushiWbtcEth",
    "native.sushiBadgerWbtc",
    "native.uniDiggWbtc",
    "native.sushiDiggWbtc",
)

# NB: Digg sett is the only sett that inherits from Sett_C
DIGG_SETT = (
    "native.digg",
)

SETT_TO_ARTIFACT_MAP = {
    SETT_A: Sett_A,
    SETT_B: Sett_B,
    DIGG_SETT: DiggSett,
}


class UpgradeSystem:
    def __init__(self, badger, deployer):
        self.badger = badger
        self.deployer = deployer
        # NB: Currently the only versioned contracts are strategy/sett contracts.
        self.contracts_upgradeable = {}
        # NB: Must define a validator for all support contract suffixes/types.
        self.validators = {
            SETT_SUFFIX: UpgradeValidator(SETT_VALIDATION_FIELDS),
            STRATEGY_SUFFIX: UpgradeValidator(STRATEGY_VALIDATION_FIELDS),
        }

    def upgrade_sett_contract(self, contractKey: str, validate: bool = False) -> None:
        self._upgrade_contract(
            SETT_SUFFIX,
            self.badger.getSettArtifact,
            contractKey=contractKey,
            validate=validate,
        )

    def upgrade_strategy_contract(self, contractKey: str, validate: bool = False) -> None:
        self._upgrade_contract(
            STRATEGY_SUFFIX,
            self.badger.getStrategyArtifact,
            contractKey=contractKey,
            validate=validate,
        )

    def upgrade_sett_contracts(self, validate: bool = False) -> None:
        self._upgrade_contract(SETT_SUFFIX, self.getSettArtifact, validate=validate)

    def upgrade_strategy_contracts(self, validate: bool = False) -> None:
        self._upgrade_contract(STRATEGY_SUFFIX, self.badger.getStrategyArtifact, validate=validate)

    def _upgrade_contract(
            self,
            suffix: str,
            getArtifactFn: lambda str: ProjectContract,
            contractKey: Optional[str] = None,
            validate: bool = False,
    ) -> None:
        # Must have a validator defined for a contract suffix/type.
        validator = self.validators[suffix]
        for key, contract in self.contracts_upgradeable.items():
            # If a contract key is specified, only attempt to upgrade that contract.
            if contractKey is not None and contractKey != key:
                continue

            if key.endswith(suffix):
                Artifact = getArtifactFn(key.removesuffix(suffix))
                latest = Artifact.deploy({"from": self.deployer})
                validator.snapshot(contract)
                upgrade_versioned_proxy(
                    self.badger,
                    contract,
                    latest,
                )
                validator.snapshot(contract)

                if validate:
                    if not validator.validate():
                        console.print("[red]=== Failed to validate upgrade non matching storage vars: {}[/red]".format(validator.snapshots))
                        raise Exception("validation failed")
                    validator.reset()

    def track_contract_upgradeable(self, key: str, contract: ProjectContract) -> None:
        self.contracts_upgradeable[key] = contract

    def getSettArtifact(self, key: str) -> ProjectContract:
        for (keys, BrownieArtifact) in SETT_TO_ARTIFACT_MAP.items():
            if key in keys:
                return BrownieArtifact
        raise Exception("{} not found in SETT_TO_ARTIFACT_MAP".format(key))


class UpgradeValidator:
    '''
    UpgradeValidator validates a sequence of snapshots taken of a contract's storage vars
    during the process of an upgrade. Normally, this is just before/after to ensure that
    the storage vars have not been affected by the upgrade. This may be extended in the future
    to perform more sophisticated validation.

    NB: OZ takes a more sophisticated approach to solve this problem (this is a js plugin) by crawling
    the AST and deriving the storage layout. We take the following more simplistic user defined varialble
    checking approach due to time constraints. Could be a future TODO project to port over the AST based approach
    and contribute back to brownie.
    See: https://github.com/OpenZeppelin/openzeppelin-upgrades/blob/master/packages/core/src/validate/query.ts#L52
    '''
    def __init__(self, fields: List[str]):
        self.fields = fields
        self.snapshots: List[Tuple[Any]] = []

    def snapshot(self, contract: ProjectContract) -> None:
        snapshot = ()
        for field in self.fields:
            try:
                snapshot += (getattr(contract, field)(),)
            except exceptions.VirtualMachineError:
                # Return None if the field doesn't exist (revert).
                snapshot += (None,)
        self.snapshots.append(snapshot)

    def validate(self) -> bool:
        prev = self.snapshots[0]
        for snapshot in self.snapshots[1:]:
            if snapshot != prev:
                return False
            prev = snapshot
        return True

    def reset(self) -> None:
        self.snapshots = []
