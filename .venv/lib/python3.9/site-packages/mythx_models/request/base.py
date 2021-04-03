"""This module contains the base request domain model."""

import abc
import logging
from typing import Dict

from mythx_models.base import BaseModel

LOGGER = logging.getLogger(__name__)


class BaseRequest(BaseModel, abc.ABC):
    """An abstract object describing requests to the MythX API."""

    @property
    @abc.abstractmethod
    def payload(self) -> Dict:
        """An abstract property returning the request's payload data.

        :return: A Python dict to be serialized into JSON format and submitted to the endpoint.
        """
        pass

    @property
    @abc.abstractmethod
    def headers(self) -> Dict:
        """An abstract property returning additional request headers.

        :return: A dict (str -> str) instance mapping header name to header content
        """
        pass

    @property
    @abc.abstractmethod
    def parameters(self) -> Dict:
        """An abstract property returning additional URL parameters.

        :return: A dict (str -> str) instance mapping parameter name to parameter content
        """
        pass

    @property
    @abc.abstractmethod
    def method(self) -> str:
        """An abstract property returning the HTTP method to perform.

        :return: The uppercase HTTP method, e.g. "POST"
        """
        pass

    @property
    @abc.abstractmethod
    def endpoint(self) -> str:
        """The API's endpoint to hit.

        :return: A string denoting the API endpoint without the host prefix
        """
        pass
