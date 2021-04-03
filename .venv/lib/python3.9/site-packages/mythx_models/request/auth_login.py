"""This module contains the AuthLoginRequest domain model."""

import json
from typing import Dict

from mythx_models.request.base import BaseRequest
from mythx_models.util import resolve_schema


class AuthLoginRequest(BaseRequest):
    """Perform an API request that performs a login action with Ethereum
    address and password."""

    with open(resolve_schema(__file__, "auth-login.json")) as sf:
        schema = json.load(sf)

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    @property
    def endpoint(self) -> str:
        """The API's login endpoint.

        :return: A string denoting the login endpoint without the host prefix
        """
        return "v1/auth/login"

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
        return self.to_dict()

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "AuthLoginRequest":
        """Create the request domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        cls.validate(d)
        return cls(username=d["username"], password=d["password"])

    def to_dict(self) -> Dict:
        """Serialize the request model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {"username": self.username, "password": self.password}
        self.validate(d)
        return d

    def __eq__(self, other: "AuthLoginRequest") -> bool:
        return all((self.username == other.username, self.password == other.password))
