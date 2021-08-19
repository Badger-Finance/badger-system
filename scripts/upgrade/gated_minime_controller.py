from ape_safe import ApeSafe
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from helpers.coingecko import fetch_usd_price, fetch_usd_price_eth
from helpers.constants import *
from helpers.gnosis_safe import (
    ApeSafeHelper,
    GnosisSafe,
    MultisigTx,
    MultisigTxMetadata,
    convert_to_test_mode,
    exec_direct,
    get_first_owner,
)
from helpers.registry import registry
from helpers.time_utils import days, hours, to_days, to_timestamp, to_utc_date
from helpers.token_utils import BalanceSnapshotter
from helpers.utils import (
    fragments_to_shares,
    initial_fragments_to_current_fragments,
    shares_to_fragments,
    to_digg_shares,
    val,
)
from rich import pretty
from rich.console import Console
from scripts.systems.aragon_system import AragonSystem
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate

console = Console()
pretty.install()

def vote_from_governance(badger, vote_ids):
    safe = ApeSafe(badger.devMultisig.address)
    helper = ApeSafeHelper(badger, safe)

    rewardsEscrow = helper.contract_from_abi(badger.rewardsEscrow.address, "RewardsEscrow", RewardsEscrow.abi)
    teamVesting = helper.contract_from_abi(badger.teamVesting.address, "SmartVesting", SmartVesting.abi)

    voting = safe.contract_from_abi(
        badger.daoBadgerTimelock.address, "IVoting", interface.IVoting.abi
    )

    aragon = AragonSystem()
    aragonVoting = aragon.getVotingAt(
        web3.toChecksumAddress("0xdc344bfb12522bf3fa58ef0d6b9a41256fc79a1b")
    )

    tokenManager = helper.contract_from_abi(web3.toChecksumAddress("0xD86F07E5D9e391Fae521B4B000b7cE639d167425"), "ITokenManager", interface.ITokenManager.abi)
    minime = helper.contract_from_abi(badger.token.address, "IMiniMe", interface.IMiniMe.abi)

    console.print("before controller", badger.token.controller())

    token_registry = registry.token_system()

    dev = accounts.at(badger.devMultisig.address, force=True)

    tokens = [
        token_registry.erc20_by_address(registry.tokens.farm),
        token_registry.erc20_by_address(registry.tokens.xSushi),
        token_registry.erc20_by_address(registry.curve.pools.sbtcCrv.token),
        token_registry.erc20_by_address(registry.curve.pools.renCrv.token),
        token_registry.erc20_by_address(registry.curve.pools.tbtcCrv.token),
        token_registry.erc20_by_address(registry.sushi.lpTokens.sushiWbtcWeth),
        token_registry.erc20_by_address(registry.tokens.dfd),
        badger.getSett("native.cvxCrv"),
        badger.getSett("native.cvx"),
    ]

    snap = BalanceSnapshotter(tokens, [badger.devMultisig, badger.dao.agent])

    snap.snap(name="Before Transfers")

    donor1 = accounts.at("0x394DCfbCf25C5400fcC147EbD9970eD34A474543", force=True)
    donor2 = accounts.at("0xbd9c69654b8f3e5978dfd138b00cb0be29f28ccf", force=True)
    
    total = badger.token.balanceOf(voting) + badger.token.balanceOf(rewardsEscrow) + badger.token.balanceOf(teamVesting) + badger.token.balanceOf(donor2) + badger.token.balanceOf(donor1)
    console.print(f"[yellow]TOTAL[/yellow]", val(total), val(Wei("10500000 ether") - total))

    chain.mine()
    assert total > Wei("10500000 ether")

    for id in vote_ids:
        console.print(f"[yellow]Vote 1[/yellow]")
        tx = voting.vote(id, True, False)
        
        # print(tx.call_trace(True))
        # chain.mine()
        
        console.print(f"[yellow]Vote 2[/yellow]")
        tx = rewardsEscrow.call(
            aragonVoting, 0, aragonVoting.vote.encode_input(id, True, False)
        )
        
        # print(tx.call_trace(True))
        # chain.mine()

        # console.print(f"[yellow]Vote 4[/yellow]")
        # tx = aragonVoting.vote(id, True, False, {'from': donor1})

        # console.print(f"[yellow]Vote 5[/yellow]")
        # tx = aragonVoting.vote(id, True, False, {'from': donor2})

        console.print(f"[yellow]Vote 3[/yellow]")
        tx = teamVesting.call(
            aragonVoting, 0, aragonVoting.vote.encode_input(id, True, False)
        )
        
        # console.log(aragonVoting.getVote(id))
        # yea = aragonVoting.getVote(id)[6]
        # console.log(yea)
        # assert yea >= Wei("10500000 ether")
        # print(tx.call_trace(True))
        chain.mine()
    
    chain.mine()
    chain.sleep(days(3))
    chain.mine()

    snap.snap(name="After Transfers")
    # snap.diff_last_two()

    # tokenManager.migrateController()

    console.print("after controller", badger.token.controller())

    helper.publish()

    

def main():
    badger = connect_badger()
    vote_ids = [37]
    vote_from_governance(badger, vote_ids=vote_ids)
