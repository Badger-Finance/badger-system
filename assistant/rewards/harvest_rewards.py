import json
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from functools import partial, wraps
from itertools import zip_longest
from pathlib import Path
from dotmap import DotMap
import toml
from brownie import *
from eth_abi import decode_single, encode_single
from eth_abi.packed import encode_abi_packed
from eth_utils import encode_hex
from toolz import valfilter, valmap
from tqdm import tqdm, trange
from click import secho
from helpers.constants import *

"""
Harvest rewards are generated when harvest() is called on the strategy
This can be tracked via the HarvestFarm() event

Skip this calculation IF:
If there were no harvests during the claim period
If there is no-one in the vault (share totalSupply() = 0)

Each user is entitled to rewards in proportion to their stakingshareseconds during the rewards period in question

- Initial holders snapshot
- Changes during the rewards period
- Ending snapshot
- User -> Weight (stakingshareseconds)

The total rewards generated during the claim period is found via the harvest event. All harvested, minus fees. This data comes from the event.

- User -> Claim (in FARM)
- TotalClaim


Confirmations:
Ensure that during the claim period, FARM was transferred to the BadgerTree in the amount specified in the event (Via Transfer() events on FARM)

Ensure the TotalClaim for the period adds up to this amount
"""
