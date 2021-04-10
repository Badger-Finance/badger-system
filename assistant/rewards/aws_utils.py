import boto3
import json
import requests
from brownie import *
from rich.console import Console
from config.env_config import env_config

console = Console()

s3 = boto3.client(
    "s3",
    aws_access_key_id=env_config.aws_access_key_id,
    aws_secret_access_key=env_config.aws_secret_access_key,
)
merkle_bucket = "badger-merkle-proofs"
rewards_bucket = "badger-json"
analytics_bucket = "badger-analytics"


def download_past_trees(number):
    trees = []
    key = "badger-tree.json"
    response = s3.list_object_versions(Prefix=key, Bucket=merkle_bucket)
    versions = response["Versions"][:number]
    for version in versions:
        console.log(version["Key"], version["VersionId"])
        ## yield version
        s3_client_obj = s3.get_object(
            Bucket=merkle_bucket, Key=version["Key"], VersionId=version["VersionId"]
        )
        trees.append(s3_client_obj["Body"].read())
    return trees


def download_latest():
    file_key = "badger-tree.json"
    console.print("Downloading file from s3: " + file_key)
    s3_clientobj = s3.get_object(Bucket=merkle_bucket, Key=file_key)
    console.log(s3_clientobj)
    s3_clientdata = s3_clientobj["Body"].read().decode()
    console.print("Downloaded file from s3: " + file_key)
    return s3_clientdata


def download_tree(fileName):
    file_key = "rewards/rewards-1-{}".format(fileName)
    console.print("Downloading file from s3: " + file_key)
    s3_clientobj = s3.get_object(Bucket=rewards_bucket, Key=file_key)
    console.log(s3_clientobj)
    s3_clientdata = s3_clientobj["Body"].read().decode()
    return s3_clientdata


def upload(fileName):
    upload_file_key = "rewards/" + fileName
    console.print("Uploading file to s3: " + upload_file_key)

    s3.upload_file(fileName, merkle_bucket, upload_file_key)


def upload_analytics(fileName, data):
    fileKey = "{}.json".format(fileName)
    s3.put_object(
        Bucket=analytics_bucket,
        Key=fileKey,
        Body=json.dumps(data,indent=4)
    )
