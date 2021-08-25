from brownie import *
from scripts.connect_account import connect_account
from scripts.get_address import get_address
from helpers.console_utils import console
from helpers.constants import MaxUint256

defaults = {
    "create2Deployer": "0x04254eba6Ba1EA9516A753C85D450E06c1Eba5a3",
    "bricked": "0x19a21Fbba3561aD53e70268caFA3D3c8db05A79C",
    "proxyAdminPassThru": "0x3F204A06AB6A6B6Bb437B58Ae39B56B906927D95",
    "proxyAdminDev": "0xC4fE5Db8D3c0d0f410D6A7496Faa4f1658d2a301",
    "proxyAdminTimelock": "0x9208E6c28959c47E58344d5f84d88F07Fca96CFC",
}


def deploy_create_2(create_2_deployer, bytecode, salt, overrides):
    console.print(f"[green]Deploying via Create2Deployer....[/green]")
    tx = create_2_deployer.deploy(bytecode, salt, overrides)
    event = tx.events["Deployed"][0]
    console.log(event)
    return event["addr"]


def main():
    dev = connect_account()

    sett = SettV3.at("0x30bCE7386e016D6038201F57D1bA52CbA7AEFeCf")
    assert sett.token() == "0xe21F631f47bFB2bC53ED134E83B8cff00e0EC054"
    token = interface.IERC20(sett.token())

    print(token.balanceOf(dev))
    print(token.balanceOf(sett))
    print(sett.balanceOf(dev))

    token.approve(sett, MaxUint256, {"from": dev})
    tx = sett.deposit(token.balanceOf(dev), {"from": dev})

    tx.call_trace()
