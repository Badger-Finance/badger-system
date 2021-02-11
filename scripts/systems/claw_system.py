import json
from datetime import datetime, timezone
from brownie import ExpiringMultiParty, ExpiringMultiPartyCreator
from dotmap import DotMap

from helpers.time_utils import ONE_HOUR, ONE_DAY
from config.badger_config import claw_config

from rich.console import Console

console = Console()


def print_to_file(claw, path):
    system = {
        "emps": {},
    }

    for key, value in claw.emps.items():
        system["emps"][key] = value.address

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

    claw = ClawSystem(
        claw_config,
        badger_deploy["deployer"],
    )
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
    '''
    NB: The claw system has no owner as it consists only of EMP (expiring mulitparty) contracts.

    EMP contracts are not pausable, and no EOAs or multisigs have any special privileges.
    UMA governance can shut the contract down through a DVM vote, which would basically just be early settlement.
    This shutdown mechanism has never been used.

    '''
    def __init__(self, deployer, config):
        self.deployer = deployer
        self.config = config
        self.empCreator = ExpiringMultiPartyCreator.at(config.empCreatorAddress)

        self.emps = DotMap()

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
        tx = self.empCreator.createExpiringMultiParty((
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
        ), {"from": self.deployer})
        empAddr = tx.events["CreatedExpiringMultiParty"]["expiringMultiPartyAddress"]
        console.print(f"[green]Deployed synthetic {syntheticName} ({syntheticSymbol}) to address {empAddr}[/green]")
        return ExpiringMultiParty.at(empAddr)

    def _get_expiration_timestamp(self) -> int:
        import time
        now = int(time.time())  # unix time is in UTC
        startDay = now - (now % ONE_DAY)
        # NB: It is recommended by UMA to set expiry @ 10:00 pm UTC on expiry date.
        startDay += (22 * ONE_HOUR)
        # Add configured number of days from start date.
        return startDay + self.config.expirationTimestampDaysDelta
