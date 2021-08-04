from assistant.rewards.aws.helpers import s3, get_bucket
from rich.console import Console
import json

console = Console()

boostsFileName = "badger-boosts.json"


def upload_boosts(test: bool, boostData):
    """Upload boosts file to aws bucket

    :param test:
    :param boostData: calculated boosts
    """
    bucket = get_bucket(test)
    console.log("Uploading file to s3://{}/{}".format(bucket, boostsFileName))
    s3.put_object(Body=str(json.dumps(boostData)), Bucket=bucket, Key=boostsFileName)
    console.log("✅ Uploaded file to s3://{}/{}".format(bucket, boostsFileName))


def download_boosts(test: bool):
    """Download latest boosts file

    :param test:
    """
    bucket = get_bucket(test)
    s3ClientObj = s3.get_object(Bucket=bucket, Key=boostsFileName)
    data = s3ClientObj["Body"].read().decode("utf-8")
    return json.loads(data)


def add_user_data(test: bool, userData):
    boosts = download_boosts(test)
    boosts["userData"] = userData
    upload_boosts(test, boosts)


def add_multipliers(test: bool, multiplierData, userMultipliers):
    boosts = download_boosts(test)
    boosts["multiplierData"] = {**boosts["multiplierData"], **multiplierData}
    for user in list(boosts["userData"].keys()):
        if user in userMultipliers:
            boosts["userData"][user] = userMultipliers[user]

    upload_boosts(test, boosts)
