"""This module contains various utility functions for MythX domain models."""

from datetime import datetime
from os import path
from typing import Dict, Union

import dateutil.parser


def deserialize_api_timestamp(timestamp_str: str) -> datetime:
    """Deserialize a JavaScript API timestamp into Python datetime format.

    :param timestamp_str: The JS timestamp, e.g. :code:`2019-01-10T01:29:38.410Z`
    :return: A Python datetime object
    """
    return dateutil.parser.parse(timestamp_str) if timestamp_str else None


def serialize_api_timestamp(ts_obj: datetime) -> Union[str, None]:
    """Serialize a Python datetime object to its JS equivalent.

    :param ts_obj: A Python datetime object
    :return: The JS timestamp, e.g. :code:`2019-01-10T01:29:38.410Z`
    """
    if not ts_obj:
        return None
    ts_str = ts_obj.strftime("%Y-%m-%dT%H:%M:%S.%f")
    # chop off last 3 digits because JS
    return ts_str[:-3] + "Z"


def dict_delete_none_fields(d: Dict) -> Dict:
    """Remove all keys that have "None" values in a dict.

    :param d: The dictionary to sanitize
    :return: The dict instance with all "None keys" removed
    """
    for k, v in list(d.items()):
        if v is None:
            del d[k]
        elif isinstance(v, dict):
            dict_delete_none_fields(v)
    return d


def resolve_schema(module_path: str, filename: str) -> str:
    """Return a path leading to the internal JSON schema files used for
    validation.

    :param module_path: The calling module's path (used as base path)
    :param filename: The JSON schema file's name
    :return: The complete path leading to the schema file (e.g. to be consumed by :code:`open()`)
    """
    return path.join(path.dirname(module_path), "schema", filename)
