from assistant.subgraph.client import fetch_sett_balances, fetch_wallet_balances
import json
import csv


def main():
    block = 7192183
    bbadger, bdigg = fetch_wallet_balances(0, 1, None, block, "bsc")
    print("Getting token balances")
    for addr, value in list(bdigg.items()):
        if value <= 0:
            del bdigg[addr]
    bdigg_lps = fetch_sett_balances(
        "0xa861Ba302674b08f7F2F24381b705870521DDfed".lower(), block, "bsc"
    )
    for addr, value in list(bdigg_lps.items()):
        if value <= 0:
            del bdigg_lps[addr]

    print("Getting lps")

    with open("bdigg_current.csv", "w") as fp:
        writer = csv.writer(fp, delimiter=",")
        writer.writerow(["address", "value"])
        writer.writerows((zip(list(bdigg.keys()), list(bdigg.values()))))

    with open("bdigg_lps_current.csv", "w") as fp:
        writer = csv.writer(fp, delimiter=",")
        writer.writerow(["address", "value"])
        writer.writerows((zip(list(bdigg_lps.keys()), list(bdigg_lps.values()))))
