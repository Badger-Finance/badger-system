import decouple

# Use debug for expanded console output
debug = False


class EnvConfig:
    def __init__(self):
        self.aws_access_key_id = decouple.config("AWS_ACCESS_KEY_ID", default="")
        self.aws_secret_access_key = decouple.config(
            "AWS_SECRET_ACCESS_KEY", default=""
        )
        self.debug = debug


env_config = EnvConfig()
