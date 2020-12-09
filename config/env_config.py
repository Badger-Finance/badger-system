import os
from dotmap import DotMap
from dotenv import load_dotenv

load_dotenv()


class EnvConfig:
    def __init__(self):
        self.primary = os.getenv("NODE_PRIMARY_URL")
        self.secondary = os.getenv("NODE_SECONDARY_URL")
        self.aws_access_key_id = (os.getenv("AWS_ACCESS_KEY_ID"),)
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")


env_config = EnvConfig()
