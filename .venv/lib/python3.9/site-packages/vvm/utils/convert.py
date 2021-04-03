from typing import Union

from semantic_version import Version


def to_vyper_version(version: Union[str, Version]) -> Version:
    if not isinstance(version, Version):
        version = Version.coerce(version.lstrip("v"))

    if version.build and not version.prerelease:
        version.prerelease = version.build
        version.build = ()

    if not version.prerelease:
        return version

    version.prerelease = tuple(i.lower() for i in version.prerelease)

    if len(version.prerelease) == 1:
        # convert e.g. `beta17` or `B17` to `beta.17`
        prerelease = version.prerelease[0]
        if not prerelease[0].isdigit() and prerelease[-1].isdigit():
            idx = prerelease.index(next(i for i in prerelease if i.isdigit()))
            version.prerelease = prerelease[:idx], prerelease[idx:]

    if version.prerelease[0] == "b":
        version.prerelease = ("beta",) + version.prerelease[1:]

    return version
