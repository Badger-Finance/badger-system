import decouple

# Use debug for expanded console output
debug = False


class EnvConfig:
    def __init__(self):
        self.aws_access_key_id = decouple.config("AWS_ACCESS_KEY_ID", default="")
        self.aws_secret_access_key = decouple.config(
            "AWS_SECRET_ACCESS_KEY", default=""
        )
        self.graph_api_key = decouple.config("GRAPH_API_KEY")
        self.debug = debug
        self.test_webhook_url = decouple.config("TEST_WEBHOOK_URL")
        self.discord_webhook_url = decouple.config("DISCORD_WEBHOOK_URL")

    def get_webhook_url(self):
        if self.debug:
            return self.test_webhook_url
        else:
            return self.discord_webhook_url


env_config = EnvConfig()
