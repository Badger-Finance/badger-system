from helpers.utils import (
    fragments_to_shares,
    initial_fragments_to_current_fragments,
    shares_to_fragments,
    to_digg_shares,
    val,
)

from helpers.token_utils import (
    BalanceSnapshotter,
    token_metadata,
    asset_to_address,
    to_token_scale,
)
from helpers.console_utils import console


class LtccRecipient:
    def __init__(self, name, address, assets):
        self.name = name
        self.address = address
        self.assets = {}

        for key, value in assets.items():
            # Scale token values with appropriate decimals for that token
            scaled_value = to_token_scale(key, value)
            self.assets[key] = scaled_value

    def get_amount(self, asset):
        console.print(asset, self.assets)
        if asset in self.assets:
            return self.assets[asset]
        else:
            return -1
