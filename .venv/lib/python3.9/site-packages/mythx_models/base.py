"""This module contains the base domain model."""

import abc
import json
import logging
from typing import Dict

import jsonschema

from mythx_models.exceptions import ValidationError

LOGGER = logging.getLogger(__name__)


class JSONSerializable(abc.ABC):
    """An abstract base class defining an interface for a JSON serializable
    class."""

    @classmethod
    def from_json(cls, json_str: str) -> "JSONSerializable":
        """Deserialize a given JSON string to the given domain model.
        Internally, this method uses the :code:`from_dict` method.

        :param json_str: The JSON string to deserialize
        :return: The concrete deserialized domain model instance
        """
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValidationError(exc)
        return cls.from_dict(parsed)

    def to_json(self) -> str:
        """Serialize the current domain model instance to a JSON string.
        Internally, this method uses the :code:`to_dict` method.

        :return: The serialized domain model JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    @abc.abstractmethod
    def from_dict(cls, d: Dict) -> "JSONSerializable":
        """An abstract method to construct the given domain model from a Python
        dict instance.

        :param d: The dict instance to deserialize
        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def to_dict(self) -> Dict:
        """An abstract method to serialize the current domain model instance to
        a Python dict.

        :return: A Python dict instance holding the serialized domain model data
        """
        pass  # pragma: no cover


class BaseModel(JSONSerializable, abc.ABC):
    """An abstract object describing responses from the MythX API."""

    schema = None

    @classmethod
    def validate(cls, candidate) -> None:
        """Validate the object's data format. This is done using a schema
        contained at the class level. If no schema is given, it is assumed that
        the request does not contain any meaningful data (e.g. an empty logout
        response) and no validation is done. If the schema validation fails, a
        :code:`ValidationError` is raised. If this method is called on a
        concrete object that does not contain a schema,

        :code:`validate` will return right away and log a warning as this behaviour might not have
        been intended by a developer.

        :param candidate: The candidate dict to check the schema against
        :return: None
        """
        # if cls.schema is None:
        #     LOGGER.warning("Cannot validate {} without a schema".format(cls.__name__))
        #     return
        # try:
        #     jsonschema.validate(candidate, cls.schema)
        # except jsonschema.ValidationError as e:
        #     raise ValidationError(e)
        pass
