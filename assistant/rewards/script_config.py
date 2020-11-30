import os
from dotmap import DotMap
from dotenv import load_dotenv

load_dotenv()

env_config = DotMap(
    primary=os.getenv("NODE_PRIMARY_URL"),
    secondary=os.getenv("NODE_BACKUP_URL"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)