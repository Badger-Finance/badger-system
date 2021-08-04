from assistant.rewards.aws.helpers import s3, get_bucket
from rich.console import Console
import json
from typing import Dict

console = Console()


def download_latest_tree(test: bool, chain: str):
    """
    Download the latest merkle tree that was uploaded for a chain
    :param chain: the chain from which to fetch the latest tree from
    """

    target = {
        "bucket": get_bucket(test),
        "key": "badger-tree-{}.json".format(chain),
    }  # badger-api production

    console.print("Downloading latest rewards file from s3: " + target["bucket"])
    s3_clientobj = s3.get_object(Bucket=target["bucket"], Key=target["key"])
    s3_clientdata = s3_clientobj["Body"].read().decode("utf-8")
    return json.loads(s3_clientdata)


def download_tree(fileName: str):
    """
    Download a specific tree based on the merkle root of that tree
    :param fileName: fileName of tree to download
    """
    upload_bucket = "badger-json"
    upload_file_key = "rewards/" + fileName

    console.print("Downloading file from s3: " + upload_file_key)

    s3_clientobj = s3.get_object(Bucket=upload_bucket, Key=upload_file_key)
    s3_clientdata = s3_clientobj["Body"].read().decode("utf-8")

    return s3_clientdata


def download_past_trees(test: bool, number: int):
    """
    Download a number of past trees
    :param number: number of trees to download from the latest
    """
    trees = []
    key = "badger-tree.json"
    bucket = get_bucket(test)
    response = s3.list_object_versions(Prefix=key, Bucket=bucket)
    versions = response["Versions"][:number]
    for version in versions:
        console.log(version["Key"], version["VersionId"])
        # yield version
        s3_client_obj = s3.get_object(
            Bucket=bucket, Key=version["Key"], VersionId=version["VersionId"]
        )
        trees.append(s3_client_obj["Body"].read())
    return trees


def upload_tree(
    fileName: str, data: Dict, bucket: str = "badger-json", publish: bool = True
):
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
