"""This module contains a middleware to fill the :code:`noCacheLookup`
field."""

import logging
from typing import Dict, Type

from mythx_models.response.base import BaseResponse

from pythx.middleware.base import BaseMiddleware

LOGGER = logging.getLogger("AnalysisCacheMiddleware")


class AnalysisCacheMiddleware(BaseMiddleware):
    """This middleware fills the :code:`noCacheLookup` field when submitting a
    new analysis job.

    This means that only :code:`process_request` carries business logic, while
    :code:`process_response` returns the input response object right away without touching it.
    """

    def __init__(self, no_cache: bool = False):
        LOGGER.debug("Initializing with no_cache=%s", no_cache)
        self.no_cache = no_cache

    def process_request(self, req: Dict) -> Dict:
        """Add the :code:`noCacheLookup` field if the request we are making is
        the submission of a new analysis job.

        Because we execute the middleware on the request data dictionary, we cannot simply
        match the domain model type here. However, based on the endpoint and the request
        method we can determine that a new job has been submitted. In any other case, we
        return the request right away without touching it.

        :param req: The request's data dictionary
        :return: The request's data dictionary, with the :code:`noCacheLookup` field filled in
        """
        if req["method"] == "POST" and req["url"].endswith("/analyses"):
            LOGGER.debug("Adding noCacheLookup=%s", self.no_cache)
            req["payload"]["noCacheLookup"] = self.no_cache
        return req

    def process_response(self, resp: Type[BaseResponse]) -> Type[BaseResponse]:
        """This method is irrelevant for adding our tool name data, so we don't
        do anything here.

        We still have to define it, though. Otherwise when calling the abstract base class'
        :code:`process_response` method, we will encounter an exception.

        :param resp: The response domain model
        :return: The very same response domain model
        """
        LOGGER.debug("Forwarding the response without any action")
        return resp
