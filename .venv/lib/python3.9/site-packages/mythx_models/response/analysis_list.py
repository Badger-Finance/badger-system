"""This module contains the AnalysisListResponse domain model."""


import json
from typing import Dict, Iterator, List

from mythx_models.exceptions import ValidationError
from mythx_models.response.analysis import Analysis
from mythx_models.response.base import BaseResponse
from mythx_models.util import resolve_schema

INDEX_ERROR_MSG = "Analysis at index {} was not fetched"


class AnalysisListResponse(BaseResponse):
    """The API response domain model for a list of analyses."""

    with open(resolve_schema(__file__, "analysis-list.json")) as sf:
        schema = json.load(sf)

    def __init__(self, analyses: List[Analysis], total: int) -> None:
        self.analyses = analyses
        self.total = total

    @classmethod
    def validate(cls, candidate) -> None:
        """Validate the response data structure and add an explicit type check.

        :param candidate: The Python dict to validate
        """
        super().validate(candidate)
        if not type(candidate) == dict:
            raise ValidationError(
                "Expected type dict but got {}".format(type(candidate))
            )

    @classmethod
    def from_dict(cls, d: dict) -> "AnalysisListResponse":
        """Create the response domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        cls.validate(d)
        analyses = [Analysis.from_dict(a) for a in d["analyses"]]
        return cls(analyses=analyses, total=d["total"])

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {
            "analyses": [a.to_dict() for a in self.analyses],
            "total": len(self.analyses),
        }
        self.validate(d)
        return d

    def __iter__(self) -> Analysis:
        """Iterate over all analyses contained in the list."""
        for analysis in self.analyses:
            yield analysis

    def __getitem__(self, idx: int) -> Analysis:
        """Get an analysis at a specific list index."""
        try:
            return self.analyses[idx]
        except IndexError:
            raise IndexError(INDEX_ERROR_MSG.format(idx))

    def __setitem__(self, idx: int, value: Analysis) -> None:
        """Set a list item to a specified value."""
        try:
            self.analyses[idx] = value
        except IndexError:
            raise IndexError(INDEX_ERROR_MSG.format(idx))

    def __delitem__(self, idx: int) -> None:
        """Delete an analysis at a specified list index."""
        try:
            del self.analyses[idx]
            self.total -= 1
        except IndexError:
            raise IndexError(INDEX_ERROR_MSG.format(idx))

    def __len__(self) -> int:
        """Get the length of the analysis list."""
        return self.total

    def __reversed__(self) -> Iterator[Analysis]:
        """Reverse the analysis list order."""
        return reversed(self.analyses)

    def __contains__(self, item) -> bool:
        """Check whether a specific analysis is contained in the list."""
        if not type(item) in (Analysis, str):
            raise ValueError(
                "Expected type Analysis or str but got {}".format(type(item))
            )
        uuid = item.uuid if type(item) == Analysis else item
        return uuid in map(lambda x: x.uuid, self.analyses)

    def __eq__(self, candidate) -> bool:
        return all((self.total == candidate.total, self.analyses == candidate.analyses))
