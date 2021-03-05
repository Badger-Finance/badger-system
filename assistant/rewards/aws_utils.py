import boto3
from brownie import *
import requests
from rich.console import Console

console = Console()


def download_latest_tree():
    from config.env_config import env_config

    s3 = boto3.client(
        "s3",
        aws_access_key_id=env_config.aws_access_key_id,
        aws_secret_access_key=env_config.aws_secret_access_key,
    )

    target = {
        "bucket": "badger-merkle-proofs",
        "key": "badger-tree.json",
    }  # badger-api production

    console.print("Downloading latest rewards file from s3: " + target["bucket"])
    s3_clientobj = s3.get_object(Bucket=target["bucket"], Key=target["key"])
    s3_clientdata = s3_clientobj["Body"].read().decode("utf-8")
    return s3_clientdata

def download(fileName):
    url = "https://m2066zr7zl.execute-api.us-east-1.amazonaws.com/rewards/{}".format(fileName)
    return requests.get(url=url).json()

def download_bucket(fileName):
    from config.env_config import env_config
    s3 = boto3.client(
        "s3",
        aws_access_key_id=env_config.aws_access_key_id,
        aws_secret_access_key=env_config.aws_secret_access_key,
    )

    upload_bucket = "badger-json"
    upload_file_key = "rewards/" + fileName

    console.print("Downloading file from s3: " + upload_file_key)

    s3_clientobj = s3.get_object(Bucket=upload_bucket, Key=upload_file_key)
    console.print(s3_clientobj)
    s3_clientdata = s3_clientobj["Body"].read().decode("utf-8")

    return s3_clientdata

def upload(fileName, bucket="badger-json"):
    from config.env_config import env_config

    # enumeration of reward api dependency upload targets
    upload_targets = [
        {
            "bucket": "badger-json",
            "key": "rewards/" + fileName,
        },  # badger-json rewards api
        {
            "bucket": "badger-staging-merkle-proofs",
            "key": "badger-tree.json",
        },  # badger-api staging
        {
            "bucket": "badger-merkle-proofs",
            "key": "badger-tree.json",
        },  # badger-api production
    ]

    s3 = boto3.client(
        "s3",
        aws_access_key_id=env_config.aws_access_key_id,
        aws_secret_access_key=env_config.aws_secret_access_key,
    )
    for target in upload_targets:
        console.print(
            "Uploading file to s3://" + target["bucket"] + "/" + target["key"]
        )
        s3.upload_file(fileName, target["bucket"], target["key"])
