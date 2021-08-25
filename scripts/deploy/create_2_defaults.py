from brownie import *
from scripts.connect_account import connect_account
from scripts.get_address import get_address
from helpers.console_utils import console
from scripts.systems.badger_system import connect_badger

defaults = {
    "create2Deployer": "0x04254eba6Ba1EA9516A753C85D450E06c1Eba5a3",
    "bricked": "0x19a21Fbba3561aD53e70268caFA3D3c8db05A79C",
    "proxyAdminPassThru": "0x3F204A06AB6A6B6Bb437B58Ae39B56B906927D95",
    "proxyAdminDev": "0xC4fE5Db8D3c0d0f410D6A7496Faa4f1658d2a301",
    "proxyAdminTimelock": "0x9208E6c28959c47E58344d5f84d88F07Fca96CFC",
    "controller": "0xc00e71719d1494886942d6277DAeA20494cf0EeC",
    "sushiWbtcWethLp": "0x30bCE7386e016D6038201F57D1bA52CbA7AEFeCf",
}


def deploy_create_2(create_2_deployer, bytecode, salt, overrides):
    console.print(f"[green]Deploying via Create2Deployer....[/green]")
    tx = create_2_deployer.deploy(bytecode, salt, overrides)
    event = tx.events["Deployed"][0]
    console.log(event)
    return event["addr"]


def main():
    # Logic deploy (deterministic or not!)
    # Proxy admin 1

    """
    Proxy for logic (deterministic via logic)
    The things that MUST BE THE SAME:
    Proxy Admin 1
    """

    # Bricked.sol
    bytecode = "0x6080604052348015600f57600080fd5b50603f80601d6000396000f3fe6080604052600080fdfea26469706673582212209412ed49e0be7e8c389456500bf6667ddf4485ee7cbb7f848dc16d2ecb5bc9a964736f6c634300060c0033"
    salt = 0

    create_2_deployer = interface.IAnyswapCreate2Deployer(defaults["create2Deployer"])

    logic = defaults["bricked"]
    proxy_admin = interface.IProxyAdmin(defaults["proxyAdminPassThru"])
    new_logic = "0x831BeEaDfC5F4e7D9ecEa045066588824be6EbAa"
    new_admin = "0x4599f2913a3db4e73aa77a304ccc21516dd7270d"

    dev = connect_account()

    deployed = deploy_create_2(
        create_2_deployer,
        bytecode,
        salt,
        {"from": dev, "gas_limit": 1500000, "allow_revert": True},
    )

    # # dev = accounts.at(proxy_admin.owner(), force=True)

    console.print(f"        Logic -> {new_logic}")
    # proxy_admin.upgrade(deployed, new_logic, {'from': dev})

    # console.print(f"        ProxyAdmin -> {new_admin}")
    # proxy_admin.changeProxyAdmin(deployed, new_admin, {'from': dev})

    # # ===== + Initialize =====

    BadgerRegistryV1.at(deployed).initialize(dev, {"from": dev})

    # # ===== - Initialize =====

    console.print(
        f"[green]🏭 Deployed {deployed} via Create2Deployer with salt {salt}[/green]"
    )


def add_and_promote_all_vaults():
    registry = BadgerRegistryV1.at("0x22765948a3d5048f3644b81792e4e1aa7ea3da4a")
    dev = connect_account()
    badger = connect_badger()

    for sett_id in badger.getAllSettIds():
        from helpers.gas_utils import gas_strategies

        gas_strategies.set_default_for_active_chain()

        sett = badger.getSett(sett_id)
        console.print(f"Adding sett {sett_id} {sett.address}")
        registry.add(sett, {"from": dev})
        registry.promote(sett, {"from": dev})
