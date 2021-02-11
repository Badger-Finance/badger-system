from .claw_system import ClawSystem, print_to_file

from config.badger_config import claw_config


def deploy_claw_minimal(deployer, printToFile=False) -> ClawSystem:
    claw = ClawSystem(deployer, claw_config)
    claw.deploy_emps()

    if printToFile:
        print_to_file(claw, claw_config.prod_json)
    return claw
