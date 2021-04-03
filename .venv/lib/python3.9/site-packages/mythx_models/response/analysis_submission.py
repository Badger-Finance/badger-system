"""This module contains the AnalysisSubmissionResponse domain model."""

import json
from typing import Any, Dict

from mythx_models.response.analysis import Analysis
from mythx_models.response.base import BaseResponse
from mythx_models.util import resolve_schema


class AnalysisSubmissionResponse(BaseResponse):
    """The API response domain model for a successful analysis job
    submission."""

    with open(resolve_schema(__file__, "analysis-submission.json")) as sf:
        schema = json.load(sf)

    def __init__(self, analysis: Analysis):
        self.analysis = analysis

    @classmethod
    def from_dict(cls, d) -> "AnalysisSubmissionResponse":
        """Create the response domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        cls.validate(d)
        return cls(analysis=Analysis.from_dict(d))

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = self.analysis.to_dict()
        self.validate(d)
        return d

    def __getattr__(self, name) -> Any:
        """Return an attribute from the internal Analysis model."""
        return getattr(self.analysis, name)

    def __eq__(self, other: "AnalysisSubmissionResponse") -> bool:
        return self.analysis == other.analysis
