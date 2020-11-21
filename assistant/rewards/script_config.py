import os
from dotmap import DotMap
from dotenv import load_dotenv

load_dotenv()

node_config = DotMap(
    primary=os.getenv("NODE_PRIMARY_URL"),
    secondary=os.getenv("NODE_BACKUP_URL")
)