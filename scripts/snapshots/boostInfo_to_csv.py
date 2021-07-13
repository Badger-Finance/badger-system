import json
import csv


def main():
    boostInfo = json.load(open("boostInfo.json"))
    with open("ethData/boostInfo_with_nft.csv", "w") as fp:
        writer = csv.writer(fp, delimiter=",")
        writer.writerow(
            ["address", "nativeBalance", "nonNativeBalance", "boost", "nftBoost"]
        )
        for addr, data in boostInfo.items():
            writer.writerow(
                [
                    addr,
                    data["nativeBalance"],
                    data["nonNativeBalance"],
                    data["boost"],
                    data["nftBoost"],
                ]
            )
