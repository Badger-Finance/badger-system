import boto3
from config.env_config import env_config

s3 = boto3.client(
    "s3",
    aws_access_key_id=env_config.aws_access_key_id,
    aws_secret_access_key=env_config.aws_secret_access_key,
)


def get_bucket(test: bool):
    return "badger-staging-merkle-proofs" if test else "badger-merkle-proofs"
