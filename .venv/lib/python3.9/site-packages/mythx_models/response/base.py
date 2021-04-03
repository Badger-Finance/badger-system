"""This module contains the base response domain model."""

import abc
import logging

from mythx_models.base import BaseModel

LOGGER = logging.getLogger(__name__)


class BaseResponse(BaseModel, abc.ABC):
    """An abstract object describing responses from the MythX API."""

    pass
