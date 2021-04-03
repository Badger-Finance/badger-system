"""This module contains the response models for the detected issues endpoint
and a report helper."""
import json
from typing import Any, Dict, Iterator, List

from mythx_models.base import JSONSerializable
from mythx_models.exceptions import ValidationError
from mythx_models.response.base import BaseResponse
from mythx_models.response.issue import Issue, SourceFormat, SourceType
from mythx_models.util import resolve_schema


class IssueReport(JSONSerializable):
    """The API response domain model for an issues report object."""

    def __init__(
        self,
        issues: List[Issue],
        source_type: SourceType,
        source_format: SourceFormat,
        source_list: List[str],
        meta_data: Dict[str, Any],
    ):
        self.issues = issues
        self.source_type = source_type
        self.source_format = source_format
        self.source_list = source_list
        self.meta_data = meta_data

    @classmethod
    def from_dict(cls, d) -> "IssueReport":
        """Create the issue report domain model from a dict.

        :param d: The dict to deserialize from
        :return: The domain model with  the data from :code:`d` filled in
        """
        return cls(
            issues=[Issue.from_dict(i) for i in d["issues"]],
            source_type=SourceType(d["sourceType"]),
            source_format=SourceFormat(d["sourceFormat"]),
            source_list=d["sourceList"],
            meta_data=d["meta"],
        )

    def to_dict(self) -> Dict:
        """Serialize the issue report domain model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {
            "issues": [i.to_dict() for i in self.issues],
            "sourceType": self.source_type,
            "sourceFormat": self.source_format,
            "sourceList": self.source_list,
            "meta": self.meta_data,
        }
        return d

    def __contains__(self, key: str) -> bool:
        return any(map(lambda i: i.swc_id == key, self.issues))

    def __len__(self) -> int:
        return len(self.issues)

    def __iter__(self) -> Iterator[Issue]:
        for issue in self.issues:
            yield issue

    def __getitem__(self, key) -> Issue:
        return self.issues[key]

    def __setitem__(self, key, value) -> None:
        self.issues[key] = value

    def __delitem__(self, key) -> None:
        del self.issues[key]

    def __eq__(self, other: "IssueReport") -> bool:
        return all(
            (
                self.issues == other.issues,
                self.source_type == other.source_type,
                self.source_format == other.source_format,
                self.source_list == other.source_list,
                self.meta_data == other.meta_data,
            )
        )


class DetectedIssuesResponse(BaseResponse):
    """The API response domain model for a report of the detected issues."""

    with open(resolve_schema(__file__, "detected-issues.json")) as sf:
        schema = json.load(sf)

    def __init__(self, issue_reports: List[IssueReport]) -> None:
        self.issue_reports = issue_reports

    @classmethod
    def from_dict(cls, d: Dict) -> "DetectedIssuesResponse":
        """Create the response domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The List to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """

        if type(d) == list:
            cls.validate(d)
            d = {"issueReports": d}
        elif type(d) == dict:
            if d.get("issueReports") is None:
                raise ValidationError(
                    "Cannot create DetectedIssuesResponse object from invalid dictionary d: {}".format(
                        d
                    )
                )

            cls.validate(d["issueReports"])
        else:
            raise ValidationError(
                "Expected list or dict but got {} of type {}".format(d, type(d))
            )

        return cls(issue_reports=[IssueReport.from_dict(i) for i in d["issueReports"]])

    def to_dict(self, as_list=False) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {"issueReports": [report.to_dict() for report in self.issue_reports]}
        self.validate(d["issueReports"])
        return d["issueReports"] if as_list else d

    def to_json(self) -> str:
        """Serialize the model to JSON format.

        Internally, this method is using the :code:`to_dict` method.

        :return: A JSON string holding the model's data
        """
        return json.dumps([report.to_dict() for report in self.issue_reports])

    def __contains__(self, key: str) -> bool:
        """Check whether a specified SWC ID is contained in any of the
        reports."""
        if not type(key) == str:
            raise ValueError(
                "Expected SWC ID of type str but got {} of type {}".format(
                    key, type(key)
                )
            )
        for report in self.issue_reports:
            if key in report:
                return True
        return False

    def __iter__(self) -> Iterator[Issue]:
        for report in self.issue_reports:
            for issue in report:
                yield issue

    def __len__(self) -> int:
        """Return the number of issues across all reports."""
        total_detected_issues = 0
        for report in self.issue_reports:
            total_detected_issues += len(report)
        return total_detected_issues

    def __getitem__(self, key: int) -> IssueReport:
        """Get an issue report at a specific index."""
        return self.issue_reports[key]

    def __setitem__(self, key: int, value: IssueReport) -> None:
        """Set an issue report at a specified index."""
        self.issue_reports[key] = value

    def __delitem__(self, key: int) -> None:
        """Delete an issue report at a specified index."""
        del self.issue_reports[key]

    def __eq__(self, other: "DetectedIssuesResponse") -> bool:
        return self.issue_reports == other.issue_reports
