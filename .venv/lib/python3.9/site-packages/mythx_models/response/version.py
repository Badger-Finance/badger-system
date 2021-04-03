"""This module contains the VersionResponse domain model."""

import json
from typing import Dict

from mythx_models.response.base import BaseResponse
from mythx_models.util import resolve_schema


class VersionResponse(BaseResponse):
    """The API response domain model for an API version request."""

    with open(resolve_schema(__file__, "version.json")) as sf:
        schema = json.load(sf)

    def __init__(
        self,
        api_version: str,
        maru_version: str,
        mythril_version: str,
        harvey_version: str,
        hashed_version: str,
    ):
        self.api_version = api_version
        self.maru_version = maru_version
        self.mythril_version = mythril_version
        self.harvey_version = harvey_version
        self.hashed_version = hashed_version

    @classmethod
    def from_dict(cls, d: Dict) -> "VersionResponse":
        """Create the response domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        cls.validate(d)
        return cls(
            api_version=d["api"],
            maru_version=d["maru"],
            mythril_version=d["mythril"],
            harvey_version=d["harvey"],
            hashed_version=d["hash"],
        )

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {
            "api": self.api_version,
            "maru": self.maru_version,
            "mythril": self.mythril_version,
            "harvey": self.harvey_version,
            "hash": self.hashed_version,
        }
        self.validate(d)
        return d

    def __eq__(self, other: "VersionResponse") -> bool:
        return all(
            (
                self.api_version == other.api_version,
                self.maru_version == other.maru_version,
                self.mythril_version == other.mythril_version,
                self.harvey_version == other.harvey_version,
                self.hashed_version == other.hashed_version,
            )
        )
