from brownie import *
from scripts.connect_account import connect_account
from scripts.get_address import get_address
from helpers.console_utils import console


def deploy_create_2(create_2_deployer, bytecode, salt, overrides):
    console.print(f"[green]Deploying via Create2Deployer....[/green]")
    tx = create_2_deployer.deploy(bytecode, salt, overrides)
    event = tx.events["Deployed"][0]
    console.log(event)
    return event["addr"]


def main():
    bytecode = "0x6080604052348015600f57600080fd5b50603f80601d6000396000f3fe6080604052600080fdfea26469706673582212209412ed49e0be7e8c389456500bf6667ddf4485ee7cbb7f848dc16d2ecb5bc9a964736f6c634300060c0033"
    salt = 0

    create_2_deployer = interface.IAnyswapCreate2Deployer(
        "0x04254eba6Ba1EA9516A753C85D450E06c1Eba5a3"
    )
    dev = connect_account()
    # dev = badger.deployer

    deployed = deploy_create_2(create_2_deployer, bytecode, salt, {"from": dev})
    console.print(
        f"[green]🏭 Deployed {deployed} via Create2Deployer with salt {salt}[/green]"
    )
