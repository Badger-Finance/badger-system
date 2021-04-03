"""This module contains the GroupListResponse domain model."""

import json
from typing import Dict, Iterator, List

from mythx_models.response.base import BaseResponse
from mythx_models.response.group import Group
from mythx_models.util import resolve_schema

INDEX_ERROR_MSG = "Group at index {} was not fetched"


class GroupListResponse(BaseResponse):
    """The API response domain model for a list of analyses."""

    with open(resolve_schema(__file__, "group-list.json")) as sf:
        schema = json.load(sf)

    def __init__(self, groups: List[Group], total: int):
        self.groups = groups
        self.total = total

    @classmethod
    def from_dict(cls, d: Dict) -> "GroupListResponse":
        """Create the response domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        cls.validate(d)
        groups = [Group.from_dict(a) for a in d["groups"]]
        return cls(groups=groups, total=d["total"])

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {"groups": [a.to_dict() for a in self.groups], "total": len(self.groups)}
        self.validate(d)
        return d

    def __iter__(self) -> Group:
        """Iterate over all the groups in the list."""
        for group in self.groups:
            yield group

    def __getitem__(self, idx: int) -> Group:
        """Get a group at a specific list index."""
        try:
            return self.groups[idx]
        except IndexError:
            raise IndexError(INDEX_ERROR_MSG.format(idx))

    def __setitem__(self, idx: int, value: Group) -> None:
        """Set a group at a specific list index."""
        try:
            self.groups[idx] = value
        except IndexError:
            raise IndexError(INDEX_ERROR_MSG.format(idx))

    def __delitem__(self, idx: int) -> None:
        """Delete a group at a specified list index."""
        try:
            del self.groups[idx]
            self.total -= 1
        except IndexError:
            raise IndexError(INDEX_ERROR_MSG.format(idx))

    def __len__(self) -> int:
        """Get the number of total group items in the list."""
        return self.total

    def __reversed__(self) -> Iterator[Group]:
        """Return the reversed group list."""
        return reversed(self.groups)

    def __contains__(self, item: Group) -> bool:
        """Check whether a given group is part of the list."""
        if not type(item) in (Group, str):
            raise ValueError("Expected type Group or str but got {}".format(type(item)))
        identifier = item.identifier if type(item) == Group else item
        return identifier in map(lambda x: x.identifier, self.groups)

    def __eq__(self, candidate: "GroupListResponse") -> bool:
        return all((self.total == candidate.total, self.groups == candidate.groups))
