from assistant.rewards.aws_utils import upload
from brownie import *
import json
from rich.console import Console

console = Console()


def main():
    contentFileName = (
        "rewards-1-"
        + "0x44f69866e3584e1995c80e1d8153ed363d414e52e31da75bf150fcf3801befb3"
        + ".json"
    )
    console.log("Saving merkle tree as {}".format(contentFileName))

    with open(contentFileName) as f:
        rewards_data = json.load(f)

    upload(
        "rewards-1-0x94bc3b798a2d9475138bcfcbedc3faa25aa0291d8ec742e9db6819f05d31aa92.json",
        rewards_data,
        publish=False,
    )
