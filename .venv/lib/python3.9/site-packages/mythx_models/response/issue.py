"""This module contains domain models regrading found issues."""

from enum import Enum
from typing import Any, Dict, List, Tuple

from mythx_models.base import JSONSerializable


class Severity(str, Enum):
    """An Enum holding the possible severities an issue can have."""

    UNKNOWN = "Unknown"
    NONE = "None"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class SourceType(str, Enum):
    """An Enum holding the possible source type values."""

    RAW_BYTECODE = "raw-bytecode"
    ETHEREUM_ADDRESS = "ethereum-address"
    SOLIDITY_CONTRACT = "solidity-contract"
    SOLIDITY_FILE = "solidity-file"


class SourceFormat(str, Enum):
    """An Enum holding the possible source format values."""

    TEXT = "text"
    SOLC_AST_LEGACY_JSON = "solc-ast-legacy-json"
    SOLC_AST_COMPACT_JSON = "solc-ast-compact-json"
    EVM_BYZANTIUM_BYTECODE = "evm-byzantium-bytecode"
    EWASM_RAW = "ewasm-raw"


class SourceMapLocation:
    def __init__(
        self, offset: int = 0, length: int = 0, file_id: int = -1, jump_type: str = "-"
    ):
        self.o = int(offset)
        self.l = int(length)
        self.f = int(file_id)
        self.j = jump_type

    @property
    def offset(self) -> int:
        return self.o

    @offset.setter
    def offset(self, value: int) -> None:
        value = int(value)
        if value <= 0:
            raise ValueError("Expected positive offset but received {}".format(value))
        self.o = int(value)

    @property
    def length(self) -> int:
        return self.l

    @length.setter
    def length(self, value: int) -> None:
        value = int(value)
        if value <= 0:
            raise ValueError("Expected positive length but received {}".format(value))
        self.l = int(value)

    @property
    def file_id(self) -> int:
        return self.f

    @file_id.setter
    def file_id(self, value: int) -> None:
        value = int(value)
        if value < -1:
            raise ValueError(
                "Expected positive file ID or -1 but received {}".format(value)
            )
        self.f = int(value)

    @property
    def jump_type(self) -> str:
        return self.j

    @jump_type.setter
    def jump_type(self, value: str) -> None:
        if value not in ("i", "o", "-"):
            raise ValueError(
                "Invalid jump type {}, must be one of i, o, -".format(value)
            )
        self.j = value

    def to_component_string(self) -> str:
        return "{}:{}:{}:{}".format(self.o, self.l, self.f, self.j)

    def __repr__(self) -> str:
        return "<SourceMapComponent ({})>".format(self.to_component_string())

    def __eq__(self, other: "SourceMapLocation") -> bool:
        return all(
            (self.o == other.o, self.l == other.l, self.f == other.f, self.j == other.j)
        )


class SourceMap:
    def __init__(self, source_map: str):
        self.components = self.decompress(source_map)

    @staticmethod
    def sourcemap_reducer(
        accumulator: Tuple[int, int, int, str], component: str
    ) -> List[str]:
        parts = component.split(":")
        full = []
        for i in range(4):
            part_exists = i < len(parts) and parts[i]
            part = parts[i] if part_exists else accumulator[i]
            full.append(part)
        return full

    def decompress(self, source_map: str) -> List[SourceMapLocation]:
        components = source_map.split(";")
        accumulator = (-1, -1, -2, "")
        result = []

        for val in components:
            curr = self.sourcemap_reducer(accumulator, val)
            accumulator = curr
            result.append(curr)

        return [SourceMapLocation(*c) for c in result]

    def compress(self) -> str:
        compressed = []
        accumulator = (-1, -1, -2, "")
        for val in self.components:
            compr = []
            for i, v in enumerate((val.offset, val.length, val.file_id, val.jump_type)):
                if accumulator[i] == v:
                    compr.append("")
                else:
                    compr.append(str(v))
            accumulator = (val.offset, val.length, val.file_id, val.jump_type)
            compressed.append(":".join(compr).rstrip(":"))
        return ";".join(compressed)

    def to_sourcemap(self) -> str:
        return self.compress()

    def __eq__(self, other: "SourceMap") -> bool:
        return self.components == other.components


class SourceLocation(JSONSerializable):
    """The domain model for a source location in a detected issue."""

    def __init__(
        self,
        source_map: str,
        source_type: SourceType,
        source_format: SourceFormat,
        source_list: List[str],
    ):
        self.source_map = SourceMap(source_map)
        self.source_type = source_type
        self.source_format = source_format
        self.source_list = source_list

    @classmethod
    def from_dict(cls, d) -> "SourceLocation":
        """Create the response domain model from a dict.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """

        return cls(
            source_map=d["sourceMap"],
            source_type=SourceType(d["sourceType"].lower()),
            source_format=SourceFormat(d["sourceFormat"].lower()),
            source_list=d["sourceList"],
        )

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """

        return {
            "sourceMap": self.source_map.to_sourcemap(),
            "sourceType": self.source_type,
            "sourceFormat": self.source_format,
            "sourceList": self.source_list,
        }

    def __eq__(self, other: "SourceLocation") -> bool:
        return all(
            (
                self.source_map.to_sourcemap() == other.source_map.to_sourcemap(),
                self.source_type == other.source_type,
                self.source_format == other.source_format,
                self.source_list == other.source_list,
            )
        )


class DecodedLocation(JSONSerializable):
    """A source location decoded by the API to line and column numbers."""

    def __init__(
        self, start_line: int = None, start_column: int = None, end_line: int = None, end_column: int = None, hidden: bool = False,
    ):
        self.start_line = start_line
        self.start_column = start_column
        self.end_line = end_line
        self.end_column = end_column
        self.hidden = hidden

    @classmethod
    def from_dict(cls, l: List) -> "DecodedLocation":
        """Create the response domain model from a dict.

        :param l: The list to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """
        return cls(
            start_line=l[0]["line"],
            start_column=l[0]["column"],
            end_line=l[1]["line"],
            end_column=l[1]["column"],
            hidden=l[2] if len(l) > 2 else False,
        )

    def to_dict(self) -> List:
        """Serialize the response model to a Python list.

        :return: A list holding the request model data
        """
        if all((self.start_line is None, self.start_column is None, self.end_line is None, self.end_column is None)):
            # handle empty source location
            return []

        return [
            {"line": self.start_line, "column": self.start_column},
            {"line": self.end_line, "column": self.end_column},
            self.hidden,
        ]

    def __eq__(self, other: "DecodedLocation") -> bool:
        return all(
            (
                self.start_line == other.start_line,
                self.start_column == other.start_column,
                self.end_line == other.end_line,
                self.end_column == other.end_column,
                self.hidden == other.hidden,
            )
        )


class Issue(JSONSerializable):
    """The API response domain model for a single issue object."""

    def __init__(
        self,
        swc_id: str,
        swc_title: str,
        description_short: str,
        description_long: str,
        severity: Severity,
        locations: List[SourceLocation],
        extra: Dict[str, Any],
        decoded_locations: List[List[DecodedLocation]] = None,
    ):
        self.swc_id = swc_id
        self.swc_title = swc_title
        self.description_short = description_short
        self.description_long = description_long
        self.severity = severity
        self.locations = locations
        self.decoded_locations = decoded_locations or []
        self.extra_data = extra

    @classmethod
    def from_dict(cls, d: Dict) -> "Issue":
        """Create the response domain model from a dict.

        :param d: The dict to deserialize from
        :return: The domain model with the data from :code:`d` filled in
        """

        locations = [
            SourceLocation(
                source_map=loc.get("sourceMap"),
                source_type=loc.get("sourceType"),
                source_format=loc.get("sourceFormat"),
                source_list=loc.get("sourceList"),
            )
            for loc in d["locations"]
        ]

        raw_decoded_locations = d.get("decodedLocations", [])
        if raw_decoded_locations and len(raw_decoded_locations):
            decoded_locations = (
                [
                    DecodedLocation.from_dict(dl) if dl else DecodedLocation()
                    for dl in raw_decoded_locations
                ]
            )
        else:
            decoded_locations = []

        return cls(
            swc_id=d["swcID"],
            swc_title=d["swcTitle"],
            description_short=d["description"]["head"],
            description_long=d["description"]["tail"],
            severity=Severity(d["severity"]) if d["severity"] else Severity.NONE,
            locations=locations,
            decoded_locations=decoded_locations,
            extra=d["extra"],
        )

    def to_dict(self) -> Dict:
        """Serialize the response model to a Python dict.

        :return: A dict holding the request model data
        """
        result = {
            "swcID": self.swc_id,
            "swcTitle": self.swc_title,
            "description": {
                "head": self.description_short,
                "tail": self.description_long,
            },
            "severity": self.severity.name.title(),
            "locations": [loc.to_dict() for loc in self.locations],
            "extra": self.extra_data,
        }
        if self.decoded_locations:
            result.update(
                {"decodedLocations": [loc.to_dict() for loc in self.decoded_locations]}
            )

        return result

    def __eq__(self, other: "Issue") -> bool:
        return all(
            (
                self.swc_id == other.swc_id,
                self.swc_title == other.swc_title,
                self.description_short == other.description_short,
                self.description_long == other.description_long,
                self.severity == other.severity,
                self.locations == other.locations,
                self.decoded_locations == other.decoded_locations,
                self.extra_data == other.extra_data,
            )
        )
