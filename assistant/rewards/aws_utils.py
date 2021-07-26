import boto3
from brownie import *
from rich.console import Console
from config.env_config import env_config
import json

console = Console()

s3 = boto3.client(
    "s3",
    aws_access_key_id=env_config.aws_access_key_id,
    aws_secret_access_key=env_config.aws_secret_access_key,
)
merkle_bucket = "badger-merkle-proofs"
rewards_bucket = "badger-json"
analytics_bucket = "badger-analytics"


def download_latest_tree(chain: str):
    """
    Download the latest merkle tree that was uploaded for a chain
    :param chain: the chain from which to fetch the latest tree from
    """
    s3 = boto3.client(
        "s3",
        aws_access_key_id=env_config.aws_access_key_id,
        aws_secret_access_key=env_config.aws_secret_access_key,
    )

    target = {
        "bucket": merkle_bucket,
        "key": "badger-tree-{}.json".format(chain),
    }  # badger-api production

    console.print("Downloading latest rewards file from s3: " + target["bucket"])
    s3_clientobj = s3.get_object(Bucket=target["bucket"], Key=target["key"])
    s3_clientdata = s3_clientobj["Body"].read().decode("utf-8")
    return s3_clientdata


def download_tree(fileName: str):
    """
    Download a specific tree based on the merkle root of that tree
    :param fileName: fileName of tree to download
    """
    upload_bucket = "badger-json"
    upload_file_key = "rewards/" + fileName

    console.print("Downloading file from s3: " + upload_file_key)

    s3_clientobj = s3.get_object(Bucket=upload_bucket, Key=upload_file_key)
    # console.print(s3_clientobj)
    s3_clientdata = s3_clientobj["Body"].read().decode("utf-8")

    return s3_clientdata


def download_past_trees(number: int):
    """
    Download a number of past trees
    :param number: number of trees to download from the latest
    """
    trees = []
    key = "badger-tree.json"
    response = s3.list_object_versions(Prefix=key, Bucket=merkle_bucket)
    versions = response["Versions"][:number]
    for version in versions:
        console.log(version["Key"], version["VersionId"])
        # yield version
        s3_client_obj = s3.get_object(
            Bucket=merkle_bucket, Key=version["Key"], VersionId=version["VersionId"]
        )
        trees.append(s3_client_obj["Body"].read())
    return trees


def upload(fileName: str, data: Dict, bucket="badger-json" : str, publish=True: bool):
    """
    Upload the badger tree to multiple buckets
    :param fileName: the filename of the uploaded bucket
    :param data: the data to push
    """
    if not publish:
        upload_targets = [
            {
                "bucket": "badger-json",
                "key": "rewards/" + fileName,
            },  # badger-json rewards api
        ]

    # enumeration of reward api dependency upload targets
    if publish:
        upload_targets = []
        upload_targets.append(
            {
                "bucket": "badger-staging-merkle-proofs",
                "key": "badger-tree.json",
            }  # badger-api staging
        )

        upload_targets.append(
            {
                "bucket": "badger-merkle-proofs",
                "key": "badger-tree.json",
            }  # badger-api production
        )

    for target in upload_targets:
        console.print(
            "Uploading file to s3://" + target["bucket"] + "/" + target["key"]
        )
        s3.put_object(
            Body=str(json.dumps(data)), Bucket=target["bucket"], Key=target["key"]
        )
        console.print(
            "✅ Uploaded file to s3://" + target["bucket"] + "/" + target["key"]
        )


def upload_boosts(test: bool):
    """
    Upload the boosts file to either prod or staging
    """
    fileName = "badger-boosts.json"

    if test:
        bucket = "badger-staging-merkle-proofs"
    else:
        bucket = "badger-merkle-proofs"
    console.log("Uploading file to s3://" + bucket + "/" + fileName)
    s3.upload_file(fileName, bucket, fileName)
    console.log("✅ Uploaded file to s3://" + bucket + "/" + fileName)


def upload_analytics(cycle:int, data):
    """
    Upload analytics data to analytics bucket
    :param cycle: which cycle to upload
    :param data: cycle information
    """
    jsonKey = "logs/{}.json".format(cycle)
    console.log("Uploading file to s3://" + analytics_bucket + "/" + jsonKey)
    s3.put_object(Body=str(json.dumps(data)), Bucket=analytics_bucket, Key=jsonKey)
    console.log("✅ Uploaded file to s3://" + analytics_bucket + "/" + jsonKey)


def upload_schedules(data):
    """
    Upload schedules to analytics bucket
    :param data: schedules to upload
    """
    jsonKey = "schedules.json"
    console.log("Uploading file to s3://" + analytics_bucket + "/" + jsonKey)
    s3.put_object(Body=str(json.dumps(data)), Bucket=analytics_bucket, Key=jsonKey)
    console.log("✅ Uploaded file to s3://" + analytics_bucket + "/" + jsonKey)
