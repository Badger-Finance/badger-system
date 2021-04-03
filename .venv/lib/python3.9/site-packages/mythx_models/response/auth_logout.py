"""This module contains the AuthLogoutResponse domain model."""


from typing import Dict

from mythx_models.exceptions import ValidationError
from mythx_models.response.base import BaseResponse


class AuthLogoutResponse(BaseResponse):
    """The API response domain model for a successful logout action."""

    @classmethod
    def from_dict(cls, d: Dict) -> "AuthLogoutResponse":
        """Create the response domain model from a dict.

        This also validates the dict's schema and raises a :code:`ValidationError`
        if any required keys are missing or the data is malformed.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        if not d == {}:
            raise ValidationError(
                "The logout response should be empty but got data: {}".format(d)
            )
        return cls()

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        d = {}
        return d
