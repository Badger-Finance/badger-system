from datetime import datetime

import pytest
from dateutil.tz import tzutc

from mythx_models.util import (
    deserialize_api_timestamp,
    dict_delete_none_fields,
    serialize_api_timestamp,
)


@pytest.mark.parametrize(
    "api_ts,datetime_ts",
    [
        (
            "2018-11-20T23:13:12.177Z",
            datetime(
                year=2018,
                month=11,
                day=20,
                hour=23,
                minute=13,
                second=12,
                microsecond=177000,
                tzinfo=tzutc(),
            ),
        ),
        (
            "2019-11-20T23:13:12.177Z",
            datetime(
                year=2019,
                month=11,
                day=20,
                hour=23,
                minute=13,
                second=12,
                microsecond=177000,
                tzinfo=tzutc(),
            ),
        ),
        (
            "2018-12-20T23:13:12.177Z",
            datetime(
                year=2018,
                month=12,
                day=20,
                hour=23,
                minute=13,
                second=12,
                microsecond=177000,
                tzinfo=tzutc(),
            ),
        ),
        (
            "2018-11-21T23:13:12.177Z",
            datetime(
                year=2018,
                month=11,
                day=21,
                hour=23,
                minute=13,
                second=12,
                microsecond=177000,
                tzinfo=tzutc(),
            ),
        ),
        (
            "2018-11-20T22:13:12.177Z",
            datetime(
                year=2018,
                month=11,
                day=20,
                hour=22,
                minute=13,
                second=12,
                microsecond=177000,
                tzinfo=tzutc(),
            ),
        ),
        (
            "2018-11-20T23:12:12.177Z",
            datetime(
                year=2018,
                month=11,
                day=20,
                hour=23,
                minute=12,
                second=12,
                microsecond=177000,
                tzinfo=tzutc(),
            ),
        ),
        (
            "2018-11-20T23:13:11.177Z",
            datetime(
                year=2018,
                month=11,
                day=20,
                hour=23,
                minute=13,
                second=11,
                microsecond=177000,
                tzinfo=tzutc(),
            ),
        ),
        (
            "2018-11-20T23:13:12.176Z",
            datetime(
                year=2018,
                month=11,
                day=20,
                hour=23,
                minute=13,
                second=12,
                microsecond=176000,
                tzinfo=tzutc(),
            ),
        ),
        (None, None),
    ],
)
def test_ts_serde(api_ts, datetime_ts):
    assert deserialize_api_timestamp(api_ts) == datetime_ts
    assert serialize_api_timestamp(datetime_ts) == api_ts


@pytest.mark.parametrize(
    "input_dict,expected",
    [
        ({"test": None}, {}),
        ({"test": "foo"}, {"test": "foo"}),
        ({"test": "foo", "bar": "baz"}, {"test": "foo", "bar": "baz"}),
        ({"test": "foo", "bar": None}, {"test": "foo"}),
        (
            {"test": "foo", "bar": {"baz": "qux"}},
            {"test": "foo", "bar": {"baz": "qux"}},
        ),
        ({"test": "foo", "bar": {"baz": None}}, {"test": "foo", "bar": {}}),
    ],
)
def test_dict_delete_none_fields(input_dict, expected):
    assert dict_delete_none_fields(input_dict) == expected
