"""This module contains domain models regarding analysis jobs."""

import logging
from enum import Enum
from typing import Dict

from inflection import underscore

from mythx_models.response.base import BaseResponse
from mythx_models.response.group import VulnerabilityStatistics
from mythx_models.util import (
    deserialize_api_timestamp,
    dict_delete_none_fields,
    serialize_api_timestamp,
)

LOGGER = logging.getLogger(__name__)


class AnalysisStatus(str, Enum):
    """An Enum describing the status an analysis job can be in."""

    QUEUED = "Queued"
    IN_PROGRESS = "In Progress"
    ERROR = "Error"
    FINISHED = "Finished"


class Analysis(BaseResponse):
    """An object describing an analysis job.

    Such a model was built, because many other API responses deliver the
    same data when it comes to analysis jobs. This makes the code more
    DRY, validation easier, and allows for recursive SerDe (e.g. mapping
    :code:`from_dict` to a deserialized JSON list of job objects.
    """

    def __init__(
        self,
        uuid: str,
        api_version: str,
        mythril_version: str,
        harvey_version: str,
        maru_version: str,
        queue_time: int,
        status: AnalysisStatus,
        submitted_at: str,
        submitted_by: str,
        main_source: str = None,
        num_sources: int = None,
        vulnerability_statistics: Dict[str, int] = None,
        run_time: int = 0,
        client_tool_name: str = None,
        error: str = None,
        info: str = None,
        group_id: str = None,
        analysis_mode: str = None,
        group_name: str = None,
        upgraded: bool = None,
        property_checking: bool = None,
        *args,
        **kwargs
    ):
        if vulnerability_statistics is None:
            self.vulnerability_statistics = None
        else:
            self.vulnerability_statistics = VulnerabilityStatistics.from_dict(
                vulnerability_statistics
            )

        self.uuid = uuid
        self.api_version = api_version
        self.mythril_version = mythril_version
        self.harvey_version = harvey_version
        self.maru_version = maru_version
        self.queue_time = queue_time
        self.run_time = run_time
        self.status = AnalysisStatus(status.title())
        self.submitted_at = deserialize_api_timestamp(submitted_at)
        self.submitted_by = submitted_by
        self.main_source = main_source
        self.num_sources = num_sources
        self.client_tool_name = client_tool_name
        self.error = error
        self.info = info
        self.group_id = group_id
        self.group_name = group_name
        self.analysis_mode = analysis_mode
        self.upgraded = upgraded
        self.property_checking = property_checking

        if args or kwargs:
            LOGGER.debug(
                "Got unexpected arguments args={}, kwargs={}".format(args, kwargs)
            )

    @classmethod
    def from_dict(cls, d) -> "Analysis":
        """Create the response domain model from a dict.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        d = {underscore(k): v for k, v in d.items()}
        if "num_vulnerabilities" in d:
            d["vulnerability_statistics"] = d.pop("num_vulnerabilities")
        return cls(**d)

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {
            "uuid": self.uuid,
            "apiVersion": self.api_version,
            "mythrilVersion": self.mythril_version,
            "harveyVersion": self.harvey_version,
            "maruVersion": self.maru_version,
            "queueTime": self.queue_time,
            "runTime": self.run_time,
            "status": self.status.title(),
            "submittedAt": serialize_api_timestamp(self.submitted_at),
            "submittedBy": self.submitted_by,
            "mainSource": self.main_source,
            "numSources": self.num_sources,
            "numVulnerabilities": self.vulnerability_statistics.to_dict()
            if self.vulnerability_statistics
            else None,
            "clientToolName": self.client_tool_name,
            "analysisMode": self.analysis_mode,
            "groupName": self.group_name,
            "groupId": self.group_id,
        }
        if self.error is not None:
            d.update({"error": self.error})
        if self.info is not None:
            d.update({"info": self.error})

        return dict_delete_none_fields(d)

    def __eq__(self, candidate: "Analysis") -> bool:
        return all(
            (
                self.uuid == candidate.uuid,
                self.api_version == candidate.api_version,
                self.mythril_version == candidate.mythril_version,
                self.harvey_version == candidate.harvey_version,
                self.maru_version == candidate.maru_version,
                self.queue_time == candidate.queue_time,
                self.run_time == candidate.run_time,
                self.status == candidate.status,
                self.submitted_at == candidate.submitted_at,
                self.submitted_by == candidate.submitted_by,
                self.main_source == candidate.main_source,
                self.num_sources == candidate.num_sources,
                self.vulnerability_statistics == candidate.vulnerability_statistics,
                self.client_tool_name == candidate.client_tool_name,
                self.error == candidate.error,
                self.info == candidate.info,
                self.group_id == candidate.group_id,
                self.analysis_mode == candidate.analysis_mode,
                self.group_name == candidate.group_name,
            )
        )

    def __repr__(self) -> str:
        return "<Analysis uuid={} status={}>".format(self.uuid, self.status)
