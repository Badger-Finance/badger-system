from assistant.rewards.aws.helpers import s3, get_bucket
from rich.console import Console
import json

console = Console()

boostsFileName = "badger-boosts.json"


def upload_boosts(test: bool, boostData):
    """Upload boosts file to aws bucket

    :param test:
    :param boostData: calculated boost information
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
    data = json.loads(s3ClientObj["Body"].read().decode("utf-8"))
    with open("badger-boosts.json", "w") as fp:
        json.dump(data, fp)
    return data


def add_user_data(test: bool, userData):
    """Upload users boost information

    :param test:
    :param userData: user boost data
    """
    boosts = download_boosts(test)
    usersUpdated = 0
    for user, data in userData.items():
        if user in boosts["userData"]:
            usersUpdated += 1
            boosts["userData"][user] = {
                "boost": data["boost"],
                "nativeBalance": data["nativeBalance"],
                "nonNativeBalance": data["nonNativeBalance"],
                "stakeRatio": data["stakeRatio"],
                "multipliers": boosts["userData"][user]["multipliers"],
            }

    console.log("Updated {} users".format(len(usersUpdated)))
    with open("badger-boosts.json", "w") as fp:
        json.dump(boosts, fp)

    upload_boosts(test, boosts)


def add_multipliers(test: bool, multiplierData, userMultipliers):
    """Upload sett and user multipliers

    :param test:
    :param multiplierData: sett multipliers
    :param userMultipliers: user multipliers
    """
    boosts = download_boosts(test)
    boosts["multiplierData"] = {**boosts["multiplierData"], **multiplierData}
    for user in list(boosts["userData"].keys()):
        if user in userMultipliers:
            boosts["userData"][user]["multipliers"] = userMultipliers[user]

    upload_boosts(test, boosts)
