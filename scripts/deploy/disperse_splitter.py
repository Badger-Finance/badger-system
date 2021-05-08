from scripts.systems.badger_system import connect_badger
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.uniswap_system import UniswapSystem
from config.badger_config import sett_config
from helpers.registry import registry
from helpers.token_utils import distribute_from_whales, BalanceSnapshotter
from helpers.registry import registry
from brownie import *


def main():
    badger = connect_badger()

    deployer = badger.deployer
    governance = badger.devMultisig
    strategist = badger.deployer
    keeper = badger.keeper
    guardian = badger.guardian

    dfdMulti = accounts.at("0x5b5cF8620292249669e1DCC73B753d01543D6Ac7", force=True)
    sharedMulti = accounts.at("0xCF7346A5E41b0821b80D5B3fdc385EEB6Dc59F44", force=True)

    logic = Disperse.at("0x3b823864cd0cbad8a1f2b65d4807906775becaa7")
    distribute_from_whales(deployer, assets=["wbtc"])

    wbtc = interface.IERC20(registry.tokens.wbtc)
    wbtc.transfer(logic, wbtc.balanceOf(deployer) // 2, {"from": deployer})

    print(logic.payees())
    print(
        logic.isPayee(dfdMulti),
        logic.isPayee(badger.devMultisig),
        logic.isPayee(deployer),
    )
    # logic.initialize([badger.devMultisig, dfdMulti], [5000, 5000], {'from': deployer})

    snap = BalanceSnapshotter([wbtc], [logic, badger.devMultisig, dfdMulti])
    snap.snap()

    # logic.disperseToken(wbtc, {"from": deployer})
    logic.disperseToken(wbtc, {"from": dfdMulti})

    snap.snap()
    snap.diff_last_two()
