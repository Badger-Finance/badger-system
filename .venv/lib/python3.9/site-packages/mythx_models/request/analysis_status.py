"""This module contains the AnalysisStatusRequest domain model."""

from typing import Dict

from mythx_models.exceptions import ValidationError
from mythx_models.request.base import BaseRequest


class AnalysisStatusRequest(BaseRequest):
    """Perform an API request that gets the status of a previously submitted
    analysis job."""

    def __init__(self, uuid: str):
        self.uuid = uuid

    @property
    def method(self) -> str:
        """The HTTP method to perform.

        :return: The uppercase HTTP method, e.g. "POST"
        """
        return "GET"

    @property
    def endpoint(self) -> str:
        """The API's analysis status endpoint.

        :return: A string denoting the status endpoint without the host prefix
        """
        return "v1/analyses/{}".format(self.uuid)

    @property
    def headers(self) -> Dict:
        """Additional request headers.

        :return: A dict (str -> str) instance mapping header name to header content
        """
        return {}

    @property
    def parameters(self) -> Dict:
        """Additional URL parameters.

        :return: A dict (str -> str) instance mapping parameter name to parameter content
        """
        return {}

    @property
    def payload(self) -> Dict:
        """The request's payload data.

        :return: A Python dict to be serialized into JSON format and submitted to the endpoint.
        """
        return {}

    @classmethod
    def from_dict(cls, d) -> "AnalysisStatusRequest":
        """Create the request domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        uuid = d.get("uuid")
        if uuid is None:
            raise ValidationError("Missing uuid field in data {}".format(d))
        return cls(uuid=uuid)

    def to_dict(self) -> Dict:
        """Serialize the request model to a Python dict.

        :return: A dict holding the request model data
        """
        return {"uuid": self.uuid}

    def __eq__(self, other: "AnalysisStatusRequest") -> bool:
        return self.uuid == other.uuid
