import boto3
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


def download_latest_tree():

    s3 = boto3.client(
        "s3",
        aws_access_key_id=env_config.aws_access_key_id,
        aws_secret_access_key=env_config.aws_secret_access_key,
    )

    target = {
        "bucket": merkle_bucket,
        "key": "badger-tree.json",
    }  # badger-api production

    console.print("Downloading latest rewards file from s3: " + target["bucket"])
    s3_clientobj = s3.get_object(Bucket=target["bucket"], Key=target["key"])
    s3_clientdata = s3_clientobj["Body"].read().decode("utf-8")
    return s3_clientdata


def download_tree(fileName):

    s3 = boto3.client(
        "s3",
        aws_access_key_id=env_config.aws_access_key_id,
        aws_secret_access_key=env_config.aws_secret_access_key,
    )

    upload_bucket = "badger-json"
    upload_file_key = "rewards/" + fileName

    console.print("Downloading file from s3: " + upload_file_key)

    s3_clientobj = s3.get_object(Bucket=upload_bucket, Key=upload_file_key)
    # console.print(s3_clientobj)
    s3_clientdata = s3_clientobj["Body"].read().decode("utf-8")

    return s3_clientdata


def download_past_trees(number):
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


def upload(fileName, bucket="badger-json", publish=True):
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
        s3.upload_file(fileName, target["bucket"], target["key"])
        console.print(
            "✅ Uploaded file to s3://" + target["bucket"] + "/" + target["key"]
        )


def upload_boosts(test):
    fileName = "badger-boosts.json"

    if test:
        bucket = "badger-staging-merkle-proofs"
    else:
        bucket = "badger-merkle-proofs"
    console.log("Uploading file to s3://" + bucket + "/" + fileName)
    s3.upload_file(fileName, bucket, fileName)
    console.log("✅ Uploaded file to s3://" + bucket + "/" + fileName)


def upload_analytics(fileName):
    bucket = "badger-analytics"
    console.log(fileName)

    jsonKey = "rewards/{}.json".format(fileName)
    console.log(jsonKey)
    pngKey = "rewards/{}.png".format(fileName)
    console.log(pngKey)

    console.log("Uploading file to s3://" + bucket + "/" + jsonKey)
    s3.upload_file("logs/{}".format(jsonKey), bucket, jsonKey)
    console.log("✅ Uploaded file to s3://" + bucket + "/" + jsonKey)

    # console.log("Uploading file to s3://" + bucket + "/" + pngKey)
    # s3.upload_file("logs/{}".format(pngKey), bucket, pngKey)
    # console.log("✅ Uploaded file to s3://" + bucket + "/" + pngKey)
