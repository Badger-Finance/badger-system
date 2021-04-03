"""This module contains the OASResponse domain model."""

import json
from typing import Dict

from mythx_models.response.base import BaseResponse
from mythx_models.util import resolve_schema


class OASResponse(BaseResponse):
    """The API response domain model for an OpenAPI request."""

    with open(resolve_schema(__file__, "openapi.json")) as sf:
        schema = json.load(sf)

    def __init__(self, data: str):
        if not type(data) == str:
            raise TypeError("Expected data type str but got {}".format(type(data)))
        self.data = data

    @classmethod
    def from_dict(cls, d: Dict) -> "OASResponse":
        """Create the response domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        cls.validate(d)
        return cls(data=d["data"])

    @classmethod
    def from_json(cls, json_str: str) -> "OASResponse":
        """

        :param json_str: The string to decode from
        :return: An OASResponse instance
        """
        # overwrite from base response because the API doesn't actually deliver
        # JSON but raw YAML/HTML
        return cls.from_dict({"data": json_str})

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {"data": self.data}
        return d

    def __eq__(self, other: "OASResponse") -> bool:
        return self.data == other.data
