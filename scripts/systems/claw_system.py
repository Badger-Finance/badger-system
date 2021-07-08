import json
import random
from datetime import datetime, timezone
from brownie import interface, ExpiringMultiParty, ExpiringMultiPartyCreator
from dotmap import DotMap

from helpers.time_utils import ONE_HOUR, ONE_DAY
from helpers.token_utils import distribute_from_whale
from helpers.registry import registry
from config.badger_config import claw_config

from rich.console import Console

console = Console()


def print_to_file(claw, path):
    system = {
        "claw_system": {"emps": {},},
    }

    for key, value in claw.emps.items():
        system["claw_system"]["emps"][key] = value.address

    with open(path, "w") as f:
        f.write(json.dumps(system, indent=4, sort_keys=True))


def connect_claw(badger_deploy_file):
    claw_deploy = {}
    console.print(
        "[grey]Connecting to Existing Claw 🦡 System at {}...[/grey]".format(
            badger_deploy_file
        )
    )
    with open(badger_deploy_file) as f:
        badger_deploy = json.load(f)
    """
    Connect to existing claw deployment
    """

    claw_deploy = badger_deploy["claw_system"]

    claw = ClawSystem(claw_config, badger_deploy["deployer"],)
    # arguments: (attr name, address)
    emps = claw_deploy["emps"]
    connectable = [
        ("sCLAW", emps["sCLAW"],),
        ("bCLAW", emps["bCLAW"],),
    ]
    for args in connectable:
        print(args)
        claw.connect_emp(*args)

    return claw


class ClawSystem:
    """
    NB: The claw system has no owner as it consists only of EMP (expiring mulitparty) contracts.

    EMP contracts are not pausable, and no EOAs or multisigs have any special privileges.
    UMA governance can shut the contract down through a DVM vote, which would basically just be early settlement.
    This shutdown mechanism has never been used.

    """

    def __init__(self, deployer, config):
        self.deployer = deployer
        self.config = config
        self.empCreator = ExpiringMultiPartyCreator.at(config.empCreatorAddress)

        self.emps = DotMap()

        # Synthetic emp lazily set for tests.
        self.emp = None
        self.empName = ""

    def connect_emp(self, attr, address) -> None:
        contract = ExpiringMultiParty.at(address)
        setattr(self.emps, attr, contract)

    # ===== Deployers =====

    def deploy_emps(self):
        for name, emp in self.config.emps.items():
            setattr(self.emps, name, self._create_emp(name, emp))

    # ===== Utility fns =====

    def _create_emp(self, name, emp) -> ExpiringMultiParty:
        expirationUnix = self._get_expiration_timestamp()
        dt = datetime.fromtimestamp(expirationUnix, tz=timezone.utc)
        syntheticName = f"{emp.symbol}-{dt.isoformat()}"
        syntheticSymbol = f"{emp.symbol}-{dt.strftime('%m-%d')}"
        # NB: This function is supposed to return the deployed EMP contract address
        # but for some reason (perhaps this is an issue w/ the mainnet fork) using that
        # address throws a `ContractNotFound` error. Pulling from the tx events does not
        # have the same issue.
        tx = self.empCreator.createExpiringMultiParty(
            (
                expirationUnix,
                emp.collateralAddress,
                emp.priceFeedIdentifier,
                syntheticName,  # long name
                syntheticSymbol,  # short name
                (self.config.collateralRequirement,),
                (self.config.disputeBondPercentage,),
                (self.config.sponsorDisputeRewardPercentage,),
                (self.config.disputerDisputeRewardPercentage,),
                (self.config.minSponsorTokens,),
                self.config.withdrawalLiveness,
                self.config.liquidationLiveness,
                self.config.excessTokenBeneficiary,
            ),
            {"from": self.deployer},
        )
        empAddr = tx.events["CreatedExpiringMultiParty"]["expiringMultiPartyAddress"]
        console.print(
            f"[green]Deployed synthetic {syntheticName} ({syntheticSymbol}) to address {empAddr}[/green]"
        )
        return ExpiringMultiParty.at(empAddr)

    def _get_expiration_timestamp(self) -> int:
        import time

        now = int(time.time())  # unix time is in UTC
        startDay = now - (now % ONE_DAY)
        # NB: It is recommended by UMA to set expiry @ 10:00 pm UTC on expiry date.
        startDay += 22 * ONE_HOUR
        # Add configured number of days from start date.
        return startDay + self.config.expirationTimestampDaysDelta

    # ===== Testing fns =====

    # Mints using currently set emp contract.
    def mint(self, user):
        collateralAddress = self.config.emps[self.empName].collateralAddress

        found = False
        whale = None
        for whale in registry.whales.values():
            if whale.token == collateralAddress:
                found = True

        if not found:
            raise Exception(
                f"whale for collateral address {collateralAddress} not found"
            )
        distribute_from_whale(whale, user)

        emp = self.emp
        collateral = interface.IERC20(collateralAddress)

        userBalance = collateral.balanceOf(user)
        collateral.approve(emp.address, userBalance, {"from": user})
        console.print(
            "[grey]Attempting to mint synthetic tokens from collateral[/grey]"
        )
        # Mint a synthetic amount is in $, we won't try to determine the actual dollar value between
        # the two but rather just mint a random dollar value above the min sponsor amount and a arbitrary max.
        # Min sponsor amount is $100 so let's do w/ $100 - $200.
        syntheticAmount = random.randint(100, 200) * 10 ** 18
        # Need to  ensure that we start w/ lower amounts of collateral as subsequent mints need must keep the total
        # position above the global collateralization ratio.
        rawTotalPositionCollateral = emp.rawTotalPositionCollateral()
        if rawTotalPositionCollateral == 0:
            # arbtirarily start the collateral low (1% of user balance)
            collateralAmount = userBalance * 0.01
        else:
            cumulativeFeeMultiplier = emp.cumulativeFeeMultiplier()
            globalCollateralizationRatio = (
                cumulativeFeeMultiplier * rawTotalPositionCollateral
            ) / emp.totalTokensOutstanding()
            minCollateralAmount = (
                globalCollateralizationRatio * syntheticAmount
            ) / cumulativeFeeMultiplier
            # collateral amount should be between the min collateral amount to keep above GCR and 5% greater.
            collateralAmount = random.randint(
                int(minCollateralAmount), int(minCollateralAmount * 1.05)
            )
        emp.create((collateralAmount,), (syntheticAmount,), {"from": user})

    def set_emp(self, empName):
        self.emp = self.emps[empName]
        self.empName = empName
