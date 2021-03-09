import boto3
from brownie import *
import requests
from rich.console import Console

console = Console()


def download(fileName):
    #s3 = boto3.client("s3")

    #upload_bucket = "badger-json"
    #upload_file_key = "rewards/" + fileName

    #console.print("Downloading file from s3: " + upload_file_key)

    #s3_clientobj = s3.get_object(Bucket=upload_bucket, Key=upload_file_key)
    # console.print(s3_clientobj)
    #s3_clientdata = s3_clientobj["Body"].read().decode("utf-8")

    #return s3_clientdata
    url = "https://d5haax09x7ee2.cloudfront.net/rewards/{}".format(fileName)
    return requests.get(url=url).json()


def upload(fileName):
    from config.env_config import env_config

    upload_bucket = "badger-json"
    upload_file_key = "rewards/" + fileName

    console.print("Uploading file to s3: " + upload_file_key)

    s3 = boto3.client(
        "s3",
        aws_access_key_id=env_config.aws_access_key_id,
        aws_secret_access_key=env_config.aws_secret_access_key,
    )
    s3.upload_file(fileName, upload_bucket, upload_file_key)
