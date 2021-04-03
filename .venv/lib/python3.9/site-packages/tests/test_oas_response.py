import json

import pytest

from mythx_models.response import OASResponse

OBJ_DATA = OASResponse.from_json("openapi stuff")


def test_oas_response_from_valid_json():
    resp = OASResponse.from_json("openapi stuff")
    assert resp.data == "openapi stuff"


def test_oas_response_from_valid_dict():
    resp = OASResponse.from_dict({"data": "openapi stuff"})
    assert resp.data == "openapi stuff"


# def test_oas_response_from_invalid_dict():
#     with pytest.raises(ValidationError):
#         OASResponse.from_dict({})


def test_oas_response_invalid_type():
    with pytest.raises(TypeError):
        OASResponse(data=1)


def test_oas_response_to_json():
    assert OBJ_DATA.to_json() == json.dumps({"data": "openapi stuff"})


def test_oas_response_to_dict():
    assert OBJ_DATA.to_dict() == {"data": "openapi stuff"}
