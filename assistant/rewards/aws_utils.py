import boto3
from brownie import *
import requests
from rich.console import Console
import json
from config.env_config import env_config

console = Console()

s3 = boto3.client(
    "s3",
    aws_access_key_id=env_config.aws_access_key_id,
    aws_secret_access_key=env_config.aws_secret_access_key,
)
def download(fileName):
    
    download_bucket = "badger-staging-merkle-proofs"
    file_key = "badger-tree.json"
    console.print("Downloading file from s3: " + file_key)
    s3_clientobj = s3.get_object(Bucket=download_bucket, Key=file_key)
    console.log(s3_clientobj)
    s3_clientdata = s3_clientobj["Body"].read().decode()
    return s3_clientdata



def upload(fileName):

    upload_bucket = "badger-json"
    upload_file_key = "rewards/" + fileName

    console.print("Uploading file to s3: " + upload_file_key)

    s3.upload_file(fileName, upload_bucket, upload_file_key)
