"""This module contains pre-defined middlewares.

This also encompasses an abstract base middleware that developers can
easily use to build their own and register it later in the APIHandler
class.
"""

from .analysiscache import AnalysisCacheMiddleware
from .base import BaseMiddleware
from .group_data import GroupDataMiddleware
from .toolname import ClientToolNameMiddleware
