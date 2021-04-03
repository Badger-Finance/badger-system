"""This module contains exceptions raised by MythX."""


class MythXBaseException(Exception):
    """A base exception describing MythX-related errors."""

    pass


class ValidationError(ValueError):
    """An exception denoting an error in SerDe of request or response data."""

    pass


class MythXAPIError(MythXBaseException):
    """An exception denoting an API-related error.

    This is usually raised when the API takes too long to respond, or a
    response contains an HTTP status code that is not 200 OK. In this
    case, the exception is passed on to the developer. This should give
    them early warnings about malformed data on their side, or recover
    in case the API is not available or experiences some kind of error
    we cannot handle.
    """

    pass
