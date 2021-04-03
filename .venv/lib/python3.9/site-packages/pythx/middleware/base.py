"""This module contains the abstract base middleware class."""

import abc
from typing import Dict, Type

from mythx_models.response.base import BaseResponse


class BaseMiddleware(abc.ABC):
    """Abstract middleware class that can be used by developers to build their
    own.

    A middleware is expected to expose two methods: :code:`process_request` and
    :code:`process_response`. Each is expected to return and updated version of their
    input. The return type must be the same as the input type.

    As middlewares are processed sequentially, it is recommended that they are kept
    associative, meaning that the order in which middlewares are executed does not
    matter. In practice, this means that a middleware should not depend on the content
    of other middlewares, or return data that could break other middlewares that are
    executed after.
    """

    @abc.abstractmethod
    def process_request(self, req: Dict) -> Dict:
        """Abstract method for a request processor.

        The implementation is expected to return an updated version of the request data
        dictionary.

        :param req: The request's data dictionary
        """
        pass

    @abc.abstractmethod
    def process_response(self, resp: Type[BaseResponse]) -> Type[BaseResponse]:
        """Abstract method for a response processor.

        The implementation is expected to return an updated version of the response
        domain model.

        :param resp: The response domain model
        """
        pass
