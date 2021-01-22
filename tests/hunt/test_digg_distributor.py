import asyncio
import concurrent.futures
from functools import partial

import json
import pytest
from brownie import accounts, reverts
from rich.console import Console

console = Console()


@pytest.fixture(scope="function", autouse="True")
def setup(digg_distributor_prod_unit):
    with open("airdrops/digg-airdrop.json") as f:
        airdrop = json.load(f)

    return (digg_distributor_prod_unit, airdrop)


# @pytest.mark.skip()
def test_all_claims_full_amount(setup):
    digg = setup[0]
    airdrop = setup[1]

    totalSharesClaimed = 0
    maxBatchSize = 100
    claims = []
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        for user, claim in airdrop["claims"].items():
            if len(claims) >= maxBatchSize:
                results = loop.run_until_complete(asyncio.gather(*claims))
                totalSharesClaimed += sum(results)
                claims = claims[:0]
                continue
            claims.append(_process_claim(loop, pool, digg, user, claim))


async def _process_claim(loop, pool, digg, user, claim):
    # Unlock their account (force=True)
    await loop.run_in_executor(
        pool,
        partial(accounts.at, user, force=True),
    )

    index = claim["index"]
    amount = int(claim["amount"], 16)
    proof = claim["proof"]
    token = digg.token
    sharesOfPartial = partial(token.sharesOf, user)
    preShares = await loop.run_in_executor(pool, sharesOfPartial)

    # Make their claim
    claimPartial = partial(
        digg.diggDistributor.claim,
        index,
        user,
        amount,
        proof,
        {"from": user},
    )
    await loop.run_in_executor(pool, claimPartial)

    # Should not be able to claim twice
    with reverts():
        await loop.run_in_executor(pool, claimPartial)

    postShares = await loop.run_in_executor(pool, sharesOfPartial)

    # Some share dust will settle in the digg distributor due to
    # shares <-> frags conversion.
    transferAmountFrags = await loop.run_in_executor(
        pool,
        partial(token.sharesToFragments, amount),
    )
    transferAmountShares = await loop.run_in_executor(
        pool,
        partial(token.fragmentsToShares, transferAmountFrags),
    )

    # Ensure their claim is correct.
    assert preShares + transferAmountShares == postShares
    assert token.sharesOf(user) == transferAmountShares

    return transferAmountShares
