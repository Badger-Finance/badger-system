#!/usr/bin/python3

import json
from pathlib import Path

from .dependencies import set_dependencies
from .nodes import node_class_factory


def from_standard_output_json(path):

    """
    Generates SourceUnit objects from a standard output json file.

    Arguments:
        path: path to the json file
    """

    output_json = json.load(Path(path).open())
    return from_standard_output(output_json)


def from_standard_output(output_json):

    """
    Generates SourceUnit objects from a standard output json as a dict.

    Arguments:
        output_json: dict of standard compiler output
    """

    source_nodes = [node_class_factory(v["ast"], None) for v in output_json["sources"].values()]
    source_nodes = set_dependencies(source_nodes)
    return source_nodes


def from_ast(ast):

    """
    Generates a SourceUnit object from the given AST. Dependencies are not set.
    """

    return node_class_factory(ast, None)
