"""This module contains the AnalysisListRequest domain model."""

from datetime import datetime
from typing import Any, Dict

import dateutil.parser

from mythx_models.exceptions import ValidationError
from mythx_models.request.base import BaseRequest


class AnalysisListRequest(BaseRequest):
    """Perform an API request that lists the logged in user's past analyses."""

    def __init__(
        self,
        offset: int = None,
        date_from: datetime = None,
        date_to: datetime = None,
        created_by: str = None,
        group_name: str = None,
        group_id: str = None,
        main_source: str = None,
    ):
        self.offset = offset
        self.date_from = date_from
        self.date_to = date_to
        self.created_by = created_by
        self.group_name = group_name
        self.group_id = group_id
        self.main_source = main_source

    @property
    def endpoint(self) -> str:
        """The API's analysis list endpoint.

        :return: A string denoting the list endpoint without the host prefix
        """
        return "v1/analyses"

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
    def from_dict(cls, d: Dict[str, Any]) -> "AnalysisListRequest":
        """Create the request domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """

        req = cls(
            offset=d.get("offset"),
            date_from=dateutil.parser.parse(d.get("dateFrom"))
            if d.get("dateFrom")
            else None,
            date_to=dateutil.parser.parse(d.get("dateTo")) if d.get("dateTo") else None,
            created_by=d.get("createdBy"),
            group_name=d.get("groupName"),
            group_id=d.get("groupId"),
            main_source=d.get("mainSource"),
        )

        return req

    def to_dict(self) -> Dict:
        """Serialize the request model to a Python dict.

        :return: A dict holding the request model data
        """
        return {
            "offset": self.offset,
            "dateFrom": self.date_from.isoformat() if self.date_from else None,
            "dateTo": self.date_from.isoformat() if self.date_from else None,
            "createdBy": self.created_by,
            "groupName": self.group_name,
            "groupId": self.group_id,
            "mainSource": self.main_source,
        }

    def __eq__(self, other: "AnalysisListRequest") -> bool:
        return all(
            (
                self.offset == other.offset,
                self.date_from == other.date_from,
                self.date_to == other.date_to,
                self.created_by == other.created_by,
                self.group_name == other.group_name,
                self.group_id == other.group_id,
                self.main_source == other.main_source,
            )
        )
