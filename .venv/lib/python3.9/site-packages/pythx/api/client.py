"""This module contains the main API Client implementation."""

import logging
from datetime import datetime
from typing import Dict, List, Type, TypeVar

import jwt
from mythx_models import request as reqmodels
from mythx_models import response as respmodels
from mythx_models.request.base import BaseRequest
from mythx_models.response.base import BaseResponse

from pythx.api.handler import APIHandler
from pythx.middleware import (
    AnalysisCacheMiddleware,
    BaseMiddleware,
    ClientToolNameMiddleware,
)

LOGGER = logging.getLogger(__name__)


class Client:
    """The main class for API interaction.

    The client makes sure that you are authenticated at all times. For authentication data it
    required either the account's Ethereum address *and* password, or a valid combination of
    access *and* refresh token. If any token expires, the client will automatically try to
    refresh the access token, or log the user in again. After that, the original request is
    executed.

    Furthermore, the client class supports various actions for high-level usage to easily submit
    new analysis jobs, check their status, get notified whether they are ready, and fetch analysis
    job report data.

    A user can inject custom middlewares. There are two required internal ones:

        1. :code:`ClientToolNameMiddleware` Fills in the :code:`clientToolName` field for new analysis submissions
        2. :code:`AnalysisCacheMiddleware` Sets the :code:`noCacheLookup` field in new analysis submissions

    These middlewares can also be overwritten by the user (even though using the Client parameters is
    recommended). If any of these middleware instances are missing in the user-defined list, e.g.
    because they simply add their own ones, the Client constructor will automatically add them with their
    default or parameter-defined values (if given).
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        api_key: str = None,
        refresh_token: str = None,
        handler: APIHandler = None,
        no_cache: bool = False,
        middlewares: List[Type[BaseMiddleware]] = None,
        api_url: str = None,
    ):
        """Instantiate a new MythX API client.

        Please note that it is not recommended to authenticate with the MythX API
        using username and password. The preferred method should be by passing the API
        key obtained from the dashboard at https://dashboard.mythx.io/ by either
        providing it as a parameter, or setting the :code:`MYTHX_API_KEY` environment
        variable.

        If a login action using username and password is chosen, the API key and JWT
        refresh token are set internally if the login attempt was successful.

        The middleware list and the API URL are directly forwarded to the API handler
        class unless a custom instance has already been provided.

        :param username: The MythX account's username
        :param password: The MythX account's password
        :param api_key: The MythX API key from the dashboard
        :param refresh_token: The JWT refresh token
        :param handler: Use a custom API handler instance
        :param no_cache: Disable the cache (special privileges required)
        :param middlewares: A list of custom middlewares to include
        :param api_url: A custom API endpoint for dedicated MythX deployments
        """
        self.username = username
        self.password = password

        if not middlewares:
            # initialize without custom middlewares
            middlewares = [
                ClientToolNameMiddleware(),
                AnalysisCacheMiddleware(no_cache),
            ]
        else:
            # add tool name and analysis cache middleware
            type_list = [type(m) for m in middlewares]
            if ClientToolNameMiddleware not in type_list:
                middlewares.append(ClientToolNameMiddleware())
            if AnalysisCacheMiddleware not in type_list:
                middlewares.append(AnalysisCacheMiddleware(no_cache))

        self.handler = handler or APIHandler(middlewares=middlewares, api_url=api_url)
        self.api_key = api_key
        self.refresh_token = refresh_token

    def _assemble_send_parse(
        self,
        req_obj: Type[BaseRequest],
        resp_model: Type[BaseResponse],
        assert_authentication: bool = True,
        include_auth_header: bool = True,
    ) -> Type[BaseResponse]:
        """Assemble the request, send it, parse and return the response.

        This method takes a request model instance and:
        1. assembles the request to conform with the API specification
        2. sends it to the API (optionally asserting the user is authenticated)
        3. parses the API response into the given response model class

        If a username/password login is given and :code:`assert_authentication` is set to True,
        this method will additionally make sure the user session is valid and if that is not
        the case, try to renew the authentication on a best-effort basis.

        :param req_obj: The request object to send to the API
        :param resp_model: The response model class to parse the requested results into
        :param assert_authentication: Auto-check authentication
        :param include_auth_header: Include authentication header on request
        :return: The parsed API response
        """
        if assert_authentication:
            self.assert_authentication()
        auth_header = (
            {"Authorization": "Bearer {}".format(self.api_key)}
            if include_auth_header
            else None
        )
        req_dict = self.handler.assemble_request(req_obj)
        LOGGER.debug("Sending request")
        resp = self.handler.send_request(req_dict, auth_header=auth_header)
        LOGGER.debug("Parsing response")
        return self.handler.parse_response(resp, resp_model)

    @staticmethod
    def _get_jwt_expiration_ts(token: str) -> datetime:
        """Decode the APIs JWT to get their expiration time in UTC.

        :param token: The JWT to perform the check on
        :return: The UTC expiration datetime object
        """
        return datetime.utcfromtimestamp((jwt.decode(token, verify=False)["exp"]))

    def assert_authentication(self) -> None:
        """Make sure the user is authenticated.

        If necessary, this method will refresh the access token, or perform another
        login to get a fresh combination of tokens if both are expired.

        :return: None
        """
        if self.api_key is not None and self.refresh_token is None:
            # Override with access token if it's the only thing we were given
            return
        elif self.api_key is None and self.refresh_token is None:
            # We haven't authenticated yet
            self.login()
            return
        now = datetime.utcnow()
        access_expiration = self._get_jwt_expiration_ts(self.api_key)
        refresh_expiration = self._get_jwt_expiration_ts(self.refresh_token)
        if now < access_expiration:
            # auth token still valid - continue
            LOGGER.debug(
                "Auth check passed, token still valid: {} < {}".format(
                    now, access_expiration
                )
            )
        elif access_expiration < now < refresh_expiration:
            # access token expired, but refresh token hasn't - use it to get new access token
            LOGGER.debug(
                "Auth refresh needed: {} < {} < {}".format(
                    access_expiration, now, refresh_expiration
                )
            )
            self.refresh()
        else:
            # refresh token has also expired - let's login again
            LOGGER.debug("Access and refresh token have expired - logging in again")
            self.login()

    def login(self) -> respmodels.AuthLoginResponse:
        """Perform a login request on the API and return the response.

        :return: :code:`AuthLoginResponse`
        """
        req = reqmodels.AuthLoginRequest(username=self.username, password=self.password)
        resp_model = self._assemble_send_parse(
            req,
            respmodels.AuthLoginResponse,
            assert_authentication=False,
            include_auth_header=False,
        )
        self.api_key = resp_model.api_key
        self.refresh_token = resp_model.refresh_token
        return resp_model

    def logout(self) -> respmodels.AuthLogoutResponse:
        """Perform a logout request on the API and return the response.

        :return: :code:`AuthLogoutResponse`
        """
        req = reqmodels.AuthLogoutRequest()
        resp_model = self._assemble_send_parse(req, respmodels.AuthLogoutResponse)
        self.api_key = None
        self.refresh_token = None
        return resp_model

    def refresh(self) -> respmodels.AuthRefreshResponse:
        """Perform a JWT refresh on the API and return the response.

        :return: :code:`AuthRefreshResponse`
        """
        req = reqmodels.AuthRefreshRequest(
            access_token=self.api_key, refresh_token=self.refresh_token
        )
        resp_model = self._assemble_send_parse(
            req,
            respmodels.AuthRefreshResponse,
            assert_authentication=False,
            include_auth_header=False,
        )
        self.api_key = resp_model.access_token
        self.refresh_token = resp_model.refresh_token
        return resp_model

    def group_list(
        self,
        offset: int = None,
        created_by: str = "",
        group_name: str = "",
        date_from: datetime = None,
        date_to: datetime = None,
    ) -> respmodels.GroupListResponse:
        """Get a list of the currently defined MythX analysis groups.

        :param offset: The number of results to skip (used for pagination)
        :param created_by: Filter the list results by the creator's user ID
        :param group_name: Filter the list results by the group's name
        :param date_from: Only display results after the given date
        :param date_to: Only display results until the given date
        :return: :code:`GroupListResponse`
        """
        req = reqmodels.GroupListRequest(
            offset=offset,
            created_by=created_by,
            group_name=group_name,
            date_from=date_from,
            date_to=date_to,
        )
        return self._assemble_send_parse(req, respmodels.GroupListResponse)

    def analysis_list(
        self,
        date_from: datetime = None,
        date_to: datetime = None,
        offset: int = None,
        created_by: str = None,
        group_name: str = None,
        group_id: str = None,
        main_source: str = None,
    ) -> respmodels.AnalysisListResponse:
        """Get a list of the user's analyses jobs.

        :param date_from: Start of the date range (optional)
        :param date_to: End of the date range (optional)
        :param offset: The number of results to skip (used for pagination)
        :param created_by: Filter analysis results based on the creator
        :param group_name: Filter analysis results based on the group name
        :param group_id: Filter analysis results based on their group ID
        :param main_source: Filter analysis results based on their main source name
        :return: :code:`AnalysisListResponse`
        """
        req = reqmodels.AnalysisListRequest(
            offset=offset,
            date_from=date_from,
            date_to=date_to,
            created_by=created_by,
            group_name=group_name,
            group_id=group_id,
            main_source=main_source,
        )
        return self._assemble_send_parse(req, respmodels.AnalysisListResponse)

    def analyze(
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
        payload: reqmodels.AnalysisSubmissionRequest = None,
    ) -> respmodels.AnalysisSubmissionResponse:
        """Submit a new analysis job.

        At least the smart contracts bytecode, or it's source code must be given. The more
        information the MythX API gets, the more precise and verbose the results will be.

        :param contract_name: The main Solidity contract's name
        :param bytecode: The EVM creation bytecode obtained
        :param source_map: The source map for the EVM creation bytecode
        :param deployed_bytecode: The deployed EVM bytecode
        :param deployed_source_map: The deployed bytecode's source map
        :param main_source: The main source file to start analysis from
        :param sources: A dictionary holding the source file data
        :param source_list: A list of source files (ordered by the source map locs)
        :param solc_version: The solc version used for compilation
        :param analysis_mode: The analysis mode
        :param payload: Directly inject an :code:`AnalysisSubmissionRequest` model
        :return: :code:`AnalysisSubmissionResponse`
        """
        req = payload or reqmodels.AnalysisSubmissionRequest(
            contract_name=contract_name,
            bytecode=bytecode,
            source_map=source_map,
            deployed_bytecode=deployed_bytecode,
            deployed_source_map=deployed_source_map,
            main_source=main_source,
            sources=sources,
            source_list=source_list,
            solc_version=solc_version,
            analysis_mode=analysis_mode,
        )
        # req.validate()
        return self._assemble_send_parse(req, respmodels.AnalysisSubmissionResponse)

    def group_status(self, group_id: str) -> respmodels.GroupStatusResponse:
        """Get the status of an analysis group by its ID.

        :param group_id: The group ID to fetch the status for
        :return: :code:`GroupStatusResponse`
        """
        req = reqmodels.GroupStatusRequest(group_id=group_id)
        return self._assemble_send_parse(req, respmodels.GroupStatusResponse)

    def status(self, uuid: str) -> respmodels.AnalysisStatusResponse:
        """Get the status of an analysis job based on its UUID.

        :param uuid: The job's UUID
        :return: :code:`AnalysisStatusResponse`
        """
        # TODO: rename to analysis_status
        req = reqmodels.AnalysisStatusRequest(uuid)
        return self._assemble_send_parse(req, respmodels.AnalysisStatusResponse)

    def analysis_ready(self, uuid: str) -> bool:
        """Return a boolean whether the analysis job with the given UUID has
        finished processing.

        :param uuid: The analysis job UUID
        :return: bool indicating whether the analysis has finished
        """
        resp = self.status(uuid)
        return (
            resp.analysis.status == respmodels.AnalysisStatus.FINISHED
            or resp.analysis.status == respmodels.AnalysisStatus.ERROR
        )

    def report(self, uuid: str) -> respmodels.DetectedIssuesResponse:
        """Get the report holding found issues for an analysis job based on its
        UUID.

        :param uuid: The analysis job UUID
        :return: :code:`DetectedIssuesResponse`
        """
        req = reqmodels.DetectedIssuesRequest(uuid)
        return self._assemble_send_parse(req, respmodels.DetectedIssuesResponse)

    def request_by_uuid(self, uuid: str) -> respmodels.AnalysisInputResponse:
        """Get the input request based on the analysis job's UUID.

        :param uuid: The analysis job UUID
        :return: :code:`AnalysisInputResponse`
        """
        req = reqmodels.AnalysisInputRequest(uuid)
        return self._assemble_send_parse(req, respmodels.AnalysisInputResponse)

    def create_group(self, group_name: str = "") -> respmodels.GroupCreationResponse:
        """Create a new group.

        :param group_name: The name of the group (max. 256 characters, optional)
        :return: :code:`GroupCreationResponse`
        """
        req = reqmodels.GroupCreationRequest(group_name=group_name)
        return self._assemble_send_parse(req, respmodels.GroupCreationResponse)

    def seal_group(self, group_id: str) -> respmodels.GroupOperationResponse:
        """Seal the group.

        This closes an open group for the submission of any further analyses.

        :param group_id: The target group ID
        :return: :code:`GroupOperationResponse`
        """
        req = reqmodels.GroupOperationRequest(group_id=group_id, type_="seal_group")
        return self._assemble_send_parse(req, respmodels.GroupOperationResponse)

    def openapi(self, mode: str = "yaml") -> respmodels.OASResponse:
        """Return the OpenAPI specification either in HTML or YAML.

        :param mode: "yaml" or "html"
        :return: :code:`OASResponse`
        """
        req = reqmodels.OASRequest(mode=mode)
        return self._assemble_send_parse(
            req,
            respmodels.OASResponse,
            assert_authentication=False,
            include_auth_header=False,
        )

    def version(self) -> respmodels.VersionResponse:
        """Call the APIs version endpoint to get its backend version numbers.

        :return: :code:`VersionResponse`
        """
        req = reqmodels.VersionRequest()
        return self._assemble_send_parse(
            req,
            respmodels.VersionResponse,
            assert_authentication=False,
            include_auth_header=False,
        )

    def __enter__(self):
        """Entry point for the client context handler.

        :return: A :code:`Client` instance
        """
        self.assert_authentication()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit point for the client context handler.

        This method takes in parameters from context execution to handle
        exceptions that might have arisen.

        :param exc_type: The exception type during context execution
        :param exc_value: The exception value from context execution
        :param traceback: The traceback from context execution
        """
        self.logout()
