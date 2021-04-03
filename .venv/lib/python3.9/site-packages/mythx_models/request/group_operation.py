"""This module contains the GroupOperation domain model."""

from typing import Dict

from mythx_models.exceptions import ValidationError
from mythx_models.request.base import BaseRequest

GROUP_OPERATION_KEYS = ("type", "group_id")


class GroupOperationRequest(BaseRequest):
    """Perform an API request that performs an action on the specified group
    ID."""

    def __init__(self, group_id: str, type_: str):
        self.group_id = group_id
        self.type = type_

    @property
    def method(self) -> str:
        """The HTTP method to perform.

        :return: The uppercase HTTP method, e.g. "POST"
        """
        return "POST"

    @property
    def endpoint(self) -> str:
        """The API's group status endpoint.

        :return: A string denoting the status endpoint without the host prefix
        """
        return "v1/analysis-groups/{}".format(self.group_id)

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
        return {"type": self.type}

    @classmethod
    def from_dict(cls, d) -> "GroupOperationRequest":
        """Create the request domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        if not all(k in d for k in GROUP_OPERATION_KEYS):
            raise ValidationError(
                "Not all required keys {} found in data {}".format(
                    GROUP_OPERATION_KEYS, d
                )
            )
        # TODO: Validate UUID and correct type
        return cls(group_id=d["group_id"], type_=d["type"])

    def to_dict(self) -> Dict:
        """Serialize the request model to a Python dict.

        :return: A dict holding the request model data
        """
        return {"group_id": self.group_id, "type": self.type}

    def __eq__(self, other: "GroupOperationRequest") -> bool:
        return all((self.group_id == other.group_id, self.type == other.type))
