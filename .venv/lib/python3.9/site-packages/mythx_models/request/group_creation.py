"""This module contains the AuthLogoutRequest domain model."""

import json
from typing import Dict

from mythx_models.request.base import BaseRequest
from mythx_models.util import resolve_schema


class GroupCreationRequest(BaseRequest):
    """Perform an API request creates a new analysis group."""

    with open(resolve_schema(__file__, "group-creation.json")) as sf:
        schema = json.load(sf)

    def __init__(self, group_name: str = ""):
        self.group_name = group_name

    @property
    def endpoint(self) -> str:
        """The API's logout endpoint.

        :return: A string denoting the group endpoint without the host prefix
        """
        return "v1/analysis-groups"

    @property
    def method(self) -> str:
        """The HTTP method to perform.

        :return: The uppercase HTTP method, e.g. "POST"
        """
        return "POST"

    @property
    def parameters(self) -> Dict:
        """Additional URL parameters.

        :return: A dict (str -> str) instance mapping parameter name to parameter content
        """
        return {}

    @property
    def headers(self) -> Dict:
        """Additional request headers.

        :return: A dict (str -> str) instance mapping header name to header content
        """
        return {}

    @property
    def payload(self) -> Dict:
        """The request's payload data.

        :return: A Python dict to be serialized into JSON format and submitted to the endpoint.
        """
        return {"groupName": self.group_name}

    @classmethod
    def from_dict(cls, d: Dict) -> "GroupCreationRequest":
        """Create the request domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        cls.validate(d)
        return cls(group_name=d["groupName"])

    def to_dict(self) -> Dict:
        """Serialize the request model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {"groupName": self.group_name}
        self.validate(d)
        return d

    def __eq__(self, other: "GroupCreationRequest") -> bool:
        return self.group_name == other.group_name
