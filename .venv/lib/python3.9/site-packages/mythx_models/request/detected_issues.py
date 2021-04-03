"""This module contains the DetectedIssuesRequest domain model."""

import json
from typing import Dict

from mythx_models.request.analysis_status import AnalysisStatusRequest
from mythx_models.util import resolve_schema


class DetectedIssuesRequest(AnalysisStatusRequest):
    """Perform an API request that lists the detected issues of a finished
    analysis job."""

    with open(resolve_schema(__file__, "detected-issues.json")) as sf:
        schema = json.load(sf)

    def __init__(self, uuid: str):
        super().__init__(uuid)
        self.uuid = uuid

    @property
    def endpoint(self) -> str:
        """The API's analysis issue report endpoint.

        :return: A string denoting the issue report endpoint without the host prefix
        """
        return "v1/analyses/{}/issues".format(self.uuid)

    @property
    def method(self) -> str:
        """The HTTP method to perform.

        :return: The uppercase HTTP method, e.g. "POST"
        """
        return "GET"

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
        return {}

    @classmethod
    def from_dict(cls, d: Dict) -> "DetectedIssuesRequest":
        """Create the request domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        cls.validate(d)
        return cls(uuid=d["uuid"])

    def to_dict(self) -> Dict:
        """Serialize the request model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {"uuid": self.uuid}
        self.validate(d)
        return d

    def __eq__(self, other: "DetectedIssuesRequest") -> bool:
        return self.uuid == other.uuid
