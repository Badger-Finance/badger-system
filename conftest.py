import pytest

# Adds base repo dir to pytest sys.path

"""
pytest looks for the conftest modules on test collection to gather custom hooks and fixtures, and in order to import the custom objects from them, pytest adds the parent directory of the conftest.py to the sys.path (in this case the repo directory).
"""
