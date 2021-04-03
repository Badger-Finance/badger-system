"""This module contains a middleware to fill the :code:`groupId`/:code:`groupName`
field."""

import logging
from typing import Dict, Type

from mythx_models.response.base import BaseResponse

from pythx.middleware.base import BaseMiddleware

LOGGER = logging.getLogger("GroupDataMiddleware")


class GroupDataMiddleware(BaseMiddleware):
    """This middleware fills the :code:`groupId` and :code:`groupName` fields
    when submitting a new analysis job.

    This means that only :code:`process_request` carries business logic, while
    :code:`process_response` returns the input response object right away without touching it.
    """

    def __init__(self, group_id: str = None, group_name: str = None):
        LOGGER.debug("Initializing")
        self.group_id = group_id
        self.group_name = group_name

    def process_request(self, req: Dict) -> Dict:
        """Add the :code:`groupId` and/or :code:`groupName` field if the
        request we are making is the submission of a new analysis job.

        Because we execute the middleware on the request data dictionary, we cannot simply
        match the domain model type here. However, based on the endpoint and the request
        method we can determine that a new job has been submitted. In any other case, we
        return the request right away without touching it.

        :param req: The request's data dictionary
        :return: The request's data dictionary, optionally with the group data field(s) filled in
        """
        if not (req["method"] == "POST" and req["url"].endswith("/analyses")):
            return req

        if self.group_id:
            LOGGER.debug("Adding group ID %s to request", self.group_id)
            req["payload"]["groupId"] = self.group_id
        if self.group_name:
            LOGGER.debug("Adding group name %s to request", self.group_name)
            req["payload"]["groupName"] = self.group_name

        return req

    def process_response(self, resp: Type[BaseResponse]) -> Type[BaseResponse]:
        """This method is irrelevant for adding our group data, so we don't do
        anything here.

        We still have to define it, though. Otherwise when calling the abstract base class'
        :code:`process_response` method, we will encounter an exception.

        :param resp: The response domain model
        :return: The very same response domain model
        """
        LOGGER.debug("Forwarding the response without any action")
        return resp
