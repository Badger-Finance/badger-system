"""This module contains domain models regarding analysis jobs."""

import logging
from enum import Enum
from typing import Dict, List

from inflection import underscore

from mythx_models.response.base import BaseResponse
from mythx_models.util import deserialize_api_timestamp, serialize_api_timestamp

LOGGER = logging.getLogger(__name__)


class GroupStatistics(BaseResponse):
    """A container class holding data about a group's analysis jobs."""

    def __init__(
        self,
        total: int,
        queued: int,
        running: int,
        failed: int,
        finished: int,
        *args,
        **kwargs
    ):
        self.total = total
        self.queued = queued
        self.running = running
        self.failed = failed
        self.finished = finished

        # if args or kwargs:
        #     LOGGER.warning(
        #         "Got unexpected arguments args={}, kwargs={}".format(args, kwargs)
        #     )

    @classmethod
    def from_dict(cls, d) -> "GroupStatistics":
        """Create the response domain model from a dict.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        d = {k: v for k, v in d.items()}
        return cls(**d)

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {
            "total": self.total,
            "queued": self.queued,
            "running": self.running,
            "failed": self.failed,
            "finished": self.finished,
        }
        return d

    def __eq__(self, other: "GroupStatistics") -> bool:
        return all(
            (
                self.total == other.total,
                self.queued == other.queued,
                self.running == other.running,
                self.failed == other.failed,
                self.finished == other.finished,
            )
        )


class VulnerabilityStatistics(BaseResponse):
    """A container class holding data about a group's vulnerabilities."""

    def __init__(
        self,
        high: int = None,
        medium: int = None,
        low: int = None,
        none: int = None,
        *args,
        **kwargs
    ):
        self.high = high
        self.medium = medium
        self.low = low
        self.none = none

        # if args or kwargs:
        #     LOGGER.warning(
        #         "Got unexpected arguments args={}, kwargs={}".format(args, kwargs)
        #     )

    @classmethod
    def from_dict(cls, d) -> "VulnerabilityStatistics":
        """Create the response domain model from a dict.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        d = {k: v for k, v in d.items()}
        return cls(**d)

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
            "none": self.none,
        }
        return d

    def __eq__(self, other: "VulnerabilityStatistics") -> bool:
        return all(
            (
                self.high == other.high,
                self.medium == other.medium,
                self.low == other.low,
                self.none == other.none,
            )
        )


class GroupState(str, Enum):
    """An Enum describing the status of an analysis group."""

    OPENED = "opened"
    SEALED = "sealed"


class Group(BaseResponse):
    """An object describing an analysis group.

    Such a model was built, because many other API responses deliver the
    same data when it comes to analysis groups. This makes the code more
    DRY, validation easier, and allows for recursive SerDe (e.g. mapping
    :code:`from_dict` to a deserialized JSON list of job objects.
    """

    def __init__(
        self,
        identifier: str,
        name: str,
        created_at: str,
        created_by: str,
        completed_at: str,
        progress: int,
        status: GroupState,
        main_source_files: List[str],
        analysis_statistics: Dict[str, int],
        vulnerability_statistics: Dict[str, int],
        *args,
        **kwargs
    ):
        self.identifier = identifier
        self.name = name
        self.created_at = deserialize_api_timestamp(created_at)
        self.created_by = created_by
        self.completed_at = deserialize_api_timestamp(completed_at)
        self.progress = progress
        self.main_source_files = main_source_files
        self.status = GroupState(status.lower())
        self.analysis_statistics = GroupStatistics.from_dict(analysis_statistics)
        self.vulnerability_statistics = VulnerabilityStatistics.from_dict(
            vulnerability_statistics
        )

        # if args or kwargs:
        #     LOGGER.warning(
        #         "Got unexpected arguments args={}, kwargs={}".format(args, kwargs)
        #     )

    @classmethod
    def from_dict(cls, d) -> "Group":
        """Create the response domain model from a dict.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        d = {underscore(k): v for k, v in d.items()}
        d["identifier"] = d.pop("id")
        d["vulnerability_statistics"] = d.pop("num_vulnerabilities")
        d["analysis_statistics"] = d.pop("num_analyses")
        return cls(**d)

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {
            "id": self.identifier,
            "name": self.name,
            "createdAt": serialize_api_timestamp(self.created_at),
            "createdBy": self.created_by,
            "completedAt": serialize_api_timestamp(self.completed_at),
            "progress": self.progress,
            "mainSourceFiles": self.main_source_files,
            "status": self.status.lower(),
            "numAnalyses": self.analysis_statistics.to_dict(),
            "numVulnerabilities": self.vulnerability_statistics.to_dict(),
        }
        return d

    def __eq__(self, other: "Group") -> bool:
        return all(
            (
                self.identifier == other.identifier,
                self.name == other.name,
                self.created_at == other.created_at,
                self.created_by == other.created_by,
                self.completed_at == other.completed_at,
                self.progress == other.progress,
                self.main_source_files == other.main_source_files,
                self.status == other.status,
                self.analysis_statistics == other.analysis_statistics,
                self.vulnerability_statistics == other.vulnerability_statistics,
            )
        )

    def __repr__(self) -> str:
        return "<Group id={} name={}>".format(self.identifier, self.name)
