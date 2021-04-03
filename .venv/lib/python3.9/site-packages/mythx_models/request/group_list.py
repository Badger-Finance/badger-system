"""This module contains the GroupListRequest domain model."""

from datetime import datetime
from typing import Any, Dict

import dateutil.parser

from mythx_models.exceptions import ValidationError
from mythx_models.request.base import BaseRequest

GROUP_LIST_KEYS = ("offset", "createdBy", "groupName", "dateFrom", "dateTo")


class GroupListRequest(BaseRequest):
    """Perform an API request that lists the logged in user's past analyses."""

    def __init__(
        self,
        offset: int,
        created_by: str,
        group_name: str,
        date_from: datetime,
        date_to: datetime,
    ):
        self.offset = offset
        self.created_by = created_by
        self.group_name = group_name
        self.date_from = date_from
        self.date_to = date_to

    @property
    def endpoint(self) -> str:
        """The API's group list endpoint.

        :return: A string denoting the list endpoint without the host prefix
        """
        return "v1/analysis-groups"

    @property
    def method(self) -> str:
        """The HTTP method to perform.

        :return: The uppercase HTTP method, e.g. "POST"
        """
        return "GET"

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
        return self.to_dict()

    @property
    def payload(self) -> Dict:
        """The request's payload data.

        :return: A Python dict to be serialized into JSON format and submitted to the endpoint.
        """
        return {}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GroupListRequest":
        """Create the request domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        if not all(k in d for k in GROUP_LIST_KEYS):
            raise ValidationError(
                "Not all required keys {} found in data {}".format(GROUP_LIST_KEYS, d)
            )
        # TODO: Validate whether offset valid integer
        req = cls(
            offset=d["offset"],
            created_by=d["createdBy"],
            group_name=d["groupName"],
            date_from=dateutil.parser.parse(d["dateFrom"]),
            date_to=dateutil.parser.parse(d["dateTo"]),
        )

        return req

    def to_dict(self) -> Dict:
        """Serialize the request model to a Python dict.

        :return: A dict holding the request model data
        """
        return {
            "offset": self.offset,
            "createdBy": self.created_by,
            "groupName": self.group_name,
            "dateFrom": self.date_from.isoformat() if self.date_from else None,
            "dateTo": self.date_to.isoformat() if self.date_to else None,
        }

    def __eq__(self, other: "GroupListRequest") -> bool:
        return all(
            (
                self.offset == other.offset,
                self.created_by == other.created_by,
                self.group_name == other.group_name,
                self.date_from == other.date_from,
                self.date_to == other.date_to,
            )
        )
