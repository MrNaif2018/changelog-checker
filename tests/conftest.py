import socket
from collections.abc import Iterator
from typing import NoReturn

import pytest
from pytest import Config, FixtureRequest, Item, Parser

# This is to ensure we patch correctly and don't send real network calls on CI

_original_connect = socket.socket.connect
_DISABLE_NETWORK = "disable_network"


class _NetworkUsageError(Exception):
    pass


def _patched_connect(self, address) -> NoReturn:
    raise _NetworkUsageError(
        "The test attempts to connect to the network. If it is expected and required "
        "for the test, enable it with the `live` test marker: `@pytest.mark.live`."
    )


@pytest.fixture
def disable_network() -> Iterator[None]:
    socket.socket.connect = _patched_connect
    yield
    socket.socket.connect = _original_connect


def pytest_addoption(parser: Parser) -> None:
    group = parser.getgroup("network")
    group.addoption(
        "--disable-network",
        action="store_true",
        dest=_DISABLE_NETWORK,
        help="Monkeypatch socket.socket.connect to disable network connection.",
    )


@pytest.fixture(autouse=True)
def _network_marker(request: FixtureRequest) -> None:
    if request.config.getoption(_DISABLE_NETWORK):
        request.getfixturevalue("disable_network")


def pytest_configure(config: Config) -> None:
    config.addinivalue_line("markers", f"{_DISABLE_NETWORK}: disable network in marked tests.")


def pytest_runtest_setup(item: Item) -> None:
    if list(item.iter_markers(name=_DISABLE_NETWORK)) and socket.socket.connect != _patched_connect:
        socket.socket.connect = _patched_connect


def pytest_runtest_teardown(item: Item) -> None:
    if list(item.iter_markers(name=_DISABLE_NETWORK)) and socket.socket.connect != _original_connect:
        socket.socket.connect = _original_connect
