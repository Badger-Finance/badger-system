"""This module contains the AnalysisSubmissionRequest domain model."""

import json
import logging
from typing import Dict, List

from mythx_models.request.base import BaseRequest
from mythx_models.util import dict_delete_none_fields, resolve_schema

LOGGER = logging.getLogger(__name__)


class AnalysisSubmissionRequest(BaseRequest):
    """Perform an API analysis job submission as a logged in user."""

    with open(resolve_schema(__file__, "analysis-submission.json")) as sf:
        schema = json.load(sf)

    def __init__(
        self,
        contract_name: str = None,
        bytecode: str = None,
        source_map: str = None,
        deployed_bytecode: str = None,
        deployed_source_map: str = None,
        main_source: str = None,
        sources: Dict[str, Dict[str, str]] = None,
        source_list: List[str] = None,
        solc_version: str = None,
        analysis_mode: str = "quick",
    ):
        self.contract_name = contract_name
        self.bytecode = bytecode
        self.source_map = source_map
        self.deployed_bytecode = deployed_bytecode
        self.deployed_source_map = deployed_source_map
        self.main_source = main_source
        self.sources = sources
        self.source_list = source_list
        self.solc_version = solc_version
        # set alias for full mode for backwards compatibility - new modes are quick, standard, deep
        self.analysis_mode = self._get_analysis_mode(analysis_mode)

    @staticmethod
    def _get_analysis_mode(mode: str) -> str:
        return "standard" if mode == "full" else mode

    @property
    def endpoint(self) -> str:
        """The API's analysis submission endpoint.

        :return: A string denoting the submission endpoint without the host prefix
        """
        return "v1/analyses"

    @property
    def method(self) -> str:
        """The HTTP method to perform.

        :return: The uppercase HTTP method, e.g. "POST"
        """
        return "POST"

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
        return {"data": self.to_dict()}

    @classmethod
    def from_dict(cls, d: Dict) -> "AnalysisSubmissionRequest":
        """Create the request domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        if d.get("analysisMode"):
            d["analysisMode"] = cls._get_analysis_mode(d["analysisMode"])

        cls.validate(d)
        return cls(
            contract_name=d.get("contractName"),
            bytecode=d.get("bytecode"),
            source_map=d.get("sourceMap"),
            deployed_bytecode=d.get("deployedBytecode"),
            deployed_source_map=d.get("deployedSourceMap"),
            main_source=d.get("mainSource"),
            sources=d.get("sources"),
            source_list=d.get("sourceList"),
            solc_version=d.get("version"),
            analysis_mode=d.get("analysisMode"),
        )

    def to_dict(self) -> Dict:
        """Serialize the request model to a Python dict.

        :return: A dict holding the request model data
        """
        base_dict = dict_delete_none_fields(
            {
                "contractName": self.contract_name,
                "bytecode": self.bytecode,
                "sourceMap": self.source_map,
                "deployedBytecode": self.deployed_bytecode,
                "deployedSourceMap": self.deployed_source_map,
                "mainSource": self.main_source,
                "sources": self.sources if self.sources else None,
                "sourceList": self.source_list if self.source_list else None,
                "version": self.solc_version,
                "analysisMode": self.analysis_mode,
            }
        )
        self.validate(base_dict)
        return base_dict

    def __eq__(self, candidate) -> bool:
        """Perform an equality check on two Request domain models."""

        return all(
            [
                self.contract_name == candidate.contract_name,
                self.bytecode == candidate.bytecode,
                self.source_map == candidate.source_map,
                self.deployed_bytecode == candidate.deployed_bytecode,
                self.deployed_source_map == candidate.deployed_source_map,
                self.main_source == candidate.main_source,
                self.sources == candidate.sources,
                self.source_list == candidate.source_list,
                self.solc_version == candidate.solc_version,
                self.analysis_mode == candidate.analysis_mode,
            ]
        )
