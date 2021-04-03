import logging
import os
import stat
import sys
import warnings
from base64 import b64encode
from pathlib import Path
from typing import Dict, List, Optional, Union

import requests
from semantic_version import Version

from vvm import wrapper
from vvm.exceptions import (
    DownloadError,
    UnexpectedVersionError,
    UnexpectedVersionWarning,
    VyperInstallationError,
    VyperNotInstalled,
)
from vvm.utils.convert import to_vyper_version
from vvm.utils.lock import get_process_lock

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


BINARY_DOWNLOAD_BASE = "https://github.com/vyperlang/vyper/releases/download/v{}/{}"
GITHUB_RELEASES = "https://api.github.com/repos/vyperlang/vyper/releases?per_page=100"

LOGGER = logging.getLogger("vvm")

VVM_BINARY_PATH_VARIABLE = "VVM_BINARY_PATH"

_default_vyper_binary = None


def _get_os_name() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform == "win32":
        return "windows"
    raise OSError(f"Unsupported OS: '{sys.platform}' - vvm supports Linux, OSX and Windows")


def get_vvm_install_folder(vvm_binary_path: Union[Path, str] = None) -> Path:
    """
    Return the directory where `vvm` stores installed `vyper` binaries.

    By default, this is `~/.vvm`

    Arguments
    ---------
    vvm_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    Path
        Subdirectory where `vyper` binaries are are saved.
    """
    if os.getenv(VVM_BINARY_PATH_VARIABLE):
        return Path(os.environ[VVM_BINARY_PATH_VARIABLE])
    elif vvm_binary_path is not None:
        return Path(vvm_binary_path)
    else:
        path = Path.home().joinpath(".vvm")
        path.mkdir(exist_ok=True)
        return path


def get_executable(
    version: Union[str, Version] = None, vvm_binary_path: Union[Path, str] = None
) -> Path:
    """
    Return the Path to an installed `vyper` binary.

    Arguments
    ---------
    version : str | Version, optional
        Installed `vyper` version to get the path of. If not given, returns the
        path of the active version.
    vvm_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    Path
        `vyper` executable.
    """
    if not version:
        if not _default_vyper_binary:
            raise VyperNotInstalled(
                "Vyper is not installed. Call vvm.get_available_vyper_versions()"
                " to view for available versions and vvm.install_vyper() to install."
            )
        return _default_vyper_binary

    version = to_vyper_version(version)
    vyper_bin = get_vvm_install_folder(vvm_binary_path).joinpath(f"vyper-{version}")
    if _get_os_name() == "windows":
        vyper_bin = vyper_bin.with_name(f"{vyper_bin.name}.exe")

    if not vyper_bin.exists():
        raise VyperNotInstalled(
            f"vyper {version} has not been installed."
            f" Use vvm.install_vyper('{version}') to install."
        )
    return vyper_bin


def set_vyper_version(
    version: Union[str, Version], silent: bool = False, vvm_binary_path: Union[Path, str] = None
) -> None:
    """
    Set the currently active `vyper` binary.

    Arguments
    ---------
    version : str | Version, optional
        Installed `vyper` version to get the path of. If not given, returns the
        path of the active version.
    silent : bool, optional
        If True, do not generate any logger output.
    vvm_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.
    """
    version = to_vyper_version(version)
    global _default_vyper_binary
    _default_vyper_binary = get_executable(version, vvm_binary_path)
    if not silent:
        LOGGER.info(f"Using vyper version {version}")


def _get_headers(headers: Optional[Dict]) -> Dict:
    if headers is None and os.getenv("GITHUB_TOKEN") is not None:
        auth = b64encode(os.environ["GITHUB_TOKEN"].encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}

    return headers or {}


def _get_releases(headers: Optional[Dict]) -> Dict:
    data = requests.get(GITHUB_RELEASES, headers=headers)
    if data.status_code != 200:
        msg = (
            f"Status {data.status_code} when getting Vyper versions from Github:"
            f" '{data.json()['message']}'"
        )
        if data.status_code == 403:
            msg += (
                "\n\nIf this issue persists, generate a Github API token and store"
                " it as the environment variable `GITHUB_TOKEN`:\n"
                "https://github.blog/2013-05-16-personal-api-tokens/"
            )
        raise ConnectionError(msg)

    return data.json()


def get_installable_vyper_versions(headers: Dict = None) -> List[Version]:
    """
    Return a list of all `vyper` versions that can be installed by vvm.

    Returns
    -------
    List
        List of Versions objects of installable `vyper` versions.
    """
    version_list = []

    headers = _get_headers(headers)

    for release in _get_releases(headers):
        version = Version.coerce(release["tag_name"].lstrip("v"))
        asset = next((i for i in release["assets"] if _get_os_name() in i["name"]), False)
        if asset:
            version_list.append(version)
    return sorted(version_list, reverse=True)


def get_installed_vyper_versions(vvm_binary_path: Union[Path, str] = None) -> List[Version]:
    """
    Return a list of currently installed `vyper` versions.

    Arguments
    ---------
    vvm_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    List
        List of Version objects of installed `vyper` versions.
    """
    install_path = get_vvm_install_folder(vvm_binary_path)
    if _get_os_name() == "windows":
        version_list = [i.stem[6:] for i in install_path.glob("vyper-*")]
    else:
        version_list = [i.name[6:] for i in install_path.glob("vyper-*")]
    return sorted([Version(i) for i in version_list], reverse=True)


def install_vyper(
    version: Union[str, Version] = "latest",
    show_progress: bool = False,
    vvm_binary_path: Union[Path, str] = None,
    headers: Dict = None,
) -> Version:
    """
    Download and install a precompiled version of `vyper`.

    Arguments
    ---------
    version : str | Version, optional
        Version of `vyper` to install. Default is the newest available version.
    show_progress : bool, optional
        If True, display a progress bar while downloading. Requires installing
        the `tqdm` package.
    vvm_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    Version
        installed vyper version
    """

    if version == "latest":
        version = get_installable_vyper_versions()[0]
    else:
        version = to_vyper_version(version)

    os_name = _get_os_name()
    process_lock = get_process_lock(str(version))

    with process_lock:
        if _check_for_installed_version(version, vvm_binary_path):
            path = get_vvm_install_folder(vvm_binary_path).joinpath(f"vyper-{version}")
            LOGGER.info(f"vyper {version} already installed at: {path}")
            return version

        headers = _get_headers(headers)
        data = _get_releases(headers)
        try:
            release = next(i for i in data if i["tag_name"] == f"v{version}")
            asset = next(i for i in release["assets"] if _get_os_name() in i["name"])
        except StopIteration:
            raise VyperInstallationError(f"Vyper binary not available for v{version}")

        install_path = get_vvm_install_folder(vvm_binary_path).joinpath(f"vyper-{version}")
        if os_name == "windows":
            install_path = install_path.with_name(f"{install_path.name}.exe")

        url = BINARY_DOWNLOAD_BASE.format(version, asset["name"])
        content = _download_vyper(url, headers, show_progress)
        with open(install_path, "wb") as fp:
            fp.write(content)

        if os_name != "windows":
            install_path.chmod(install_path.stat().st_mode | stat.S_IEXEC)

        _validate_installation(version, vvm_binary_path)

    return version


def _check_for_installed_version(
    version: Version, vvm_binary_path: Union[Path, str] = None
) -> bool:
    path = get_vvm_install_folder(vvm_binary_path).joinpath(f"vyper-{version}")
    return path.exists()


def _download_vyper(url: str, headers: Dict, show_progress: bool) -> bytes:
    LOGGER.info(f"Downloading from {url}")
    response = requests.get(url, headers=headers, stream=show_progress)
    if response.status_code == 404:
        raise DownloadError(
            "404 error when attempting to download from {} - are you sure this"
            " version of vyper is available?".format(url)
        )
    if response.status_code != 200:
        raise DownloadError(
            f"Received status code {response.status_code} when attempting to download from {url}"
        )
    if not show_progress:
        return response.content

    total_size = int(response.headers.get("content-length", 0))
    progress_bar = tqdm(total=total_size, unit="iB", unit_scale=True)
    content = bytes()

    for data in response.iter_content(1024, decode_unicode=True):
        progress_bar.update(len(data))
        content += data
    progress_bar.close()

    return content


def _validate_installation(version: Version, vvm_binary_path: Union[Path, str, None]) -> None:
    binary_path = get_executable(version, vvm_binary_path)
    try:
        installed_version = wrapper._get_vyper_version(binary_path)
    except Exception:
        binary_path.unlink()
        raise VyperInstallationError(
            "Downloaded binary would not execute, or returned unexpected output."
        )
    if installed_version.truncate() != version.truncate():
        binary_path.unlink()
        raise UnexpectedVersionError(
            f"Attempted to install vyper v{version}, but got vyper v{installed_version}"
        )
    if "".join(installed_version.prerelease) != "".join(version.prerelease):
        # join prerelease items so we don't warn when `beta.17` is actually `beta17`
        warnings.warn(f"Installed vyper version is v{installed_version}", UnexpectedVersionWarning)
    if not _default_vyper_binary:
        set_vyper_version(version)
    LOGGER.info(f"vyper {version} successfully installed at: {binary_path}")


if get_installed_vyper_versions():
    set_vyper_version(get_installed_vyper_versions()[0], silent=True)
