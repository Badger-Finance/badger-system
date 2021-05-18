"""
Label    Rarity    Contract    Type    TokenId
Honeypot 1    500    0xe4605d46fd0b3f8329d936a8b258d69276cba264    Partner    97
Honeypot 2    500    0xe4605d46fd0b3f8329d936a8b258d69276cba264    Partner    98
Honeypot 3    100    0xe4605d46fd0b3f8329d936a8b258d69276cba264    Partner    99
Honeypot 4    100    0xe4605d46fd0b3f8329d936a8b258d69276cba264    Partner    100
Honeypot 5    10    0xe4605d46fd0b3f8329d936a8b258d69276cba264    Partner    101
Honeypot 6    10    0xe4605d46fd0b3f8329d936a8b258d69276cba264    Partner    102
Diamond Hands 1    200    0xe4605d46fd0b3f8329d936a8b258d69276cba264    Collab    205
Diamond Hands 2    50    0xe4605d46fd0b3f8329d936a8b258d69276cba264    Collab    206
Diamond Hands 3    10    0xe4605d46fd0b3f8329d936a8b258d69276cba264    Collab    208
Jersey    200    0xe1e546e25a5ed890dff8b8d005537c0d373497f8    Badger    1
"""
import math
import json
from assistant.subgraph.client import fetch_nfts
from rich.console import Console

console = Console()

MAX_NFT_BOOST = 0.5

score_multipliers = {"partner": 1, "collab": 2, "badger": 5}

honeypot_rarity = {97: 500, 98: 500, 99: 100, 100: 100, 101: 10, 102: 10}
diamond_hands_rarity = {205: 200, 206: 50, 208: 10}
jersey_rarity = {1: 200}
memeAddress = "0xe4605d46fd0b3f8329d936a8b258d69276cba264"
badgerNftAddress = "0xe1e546e25a5ed890dff8b8d005537c0d373497f8"


def calc_total_nfts_score(rarities, multiplier_type):
    return sum(
        [
            calc_score(int(k), score_multipliers[multiplier_type])
            for k in rarities.values()
        ]
    )


def calc_nft_multipliers(block):
    users = fetch_nfts(block)
    userScores = {}
    userNfts = {}
    nftMultipliers = {}
    for user in users:
        addr = user["id"]
        nfts = user["tokens"]
        sumScores = 0
        userNfts[addr] = []
        for nft in nfts:
            score = calc_nft_score(nft)
            if score > 0:
                sumScores += score
                userNfts[addr].append(nft)

        if sumScores == 0:
            continue
        else:
            userScores[addr] = sumScores

    totalHoneypotScore = calc_total_nfts_score(honeypot_rarity, "partner")
    totalDiamondScore = calc_total_nfts_score(diamond_hands_rarity, "collab")
    totalJerseyScore = calc_total_nfts_score(jersey_rarity, "badger")
    maxScore = totalJerseyScore + totalHoneypotScore + totalDiamondScore
    console.log("Max NFT score: {}".format((maxScore)))

    for addr, score in userScores.items():
        mult = (score / maxScore * 0.5) + 1
        nftMultipliers[addr] = {
            "score": score,
            "multiplier": mult,
            "nfts": userNfts[addr],
        }
    console.log(nftMultipliers)

    return nftMultipliers


def calc_percentages(d, max_score):
    for k, v in d.items():
        d[k] = (v / max_score) * 0.5
    return d


def calc_nft_score(nft):
    tokenId = int(nft["token"]["tokenId"])
    nftAddress = nft["token"]["id"].split("-")[0]
    if nftAddress == memeAddress:

        if tokenId in honeypot_rarity.keys():
            return honeypot_score(nft)
        elif tokenId in diamond_hands_rarity.keys():
            return diamond_hands_score(nft)
    if nftAddress == badgerNftAddress:
        if tokenId in jersey_rarity.keys():
            return jersey_score(nft)
    return 0


def calc_score(rarity, multiplier):
    exponent = 1 / multiplier
    denom = math.pow(math.sqrt(rarity), exponent)
    return 1000 / denom


def honeypot_score(honeypot_nft):
    tokenId = int(honeypot_nft["token"]["tokenId"])
    return calc_score(honeypot_rarity[tokenId], score_multipliers["partner"])


def diamond_hands_score(diamond_hand_nft):
    tokenId = int(diamond_hand_nft["token"]["tokenId"])
    return calc_score(diamond_hands_rarity[tokenId], score_multipliers["collab"])


def jersey_score(jersey_nft):
    tokenId = int(jersey_nft["token"]["tokenId"])
    return calc_score(jersey_rarity[tokenId], score_multipliers["badger"])
