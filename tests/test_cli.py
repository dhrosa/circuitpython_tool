import re
from contextlib import contextmanager
from pathlib import Path

import pytest

from circuitpython_tool import cli, device


@contextmanager
def exits_with_code(code):
    try:
        yield
    except SystemExit as exit:
        assert exit.code == code
    else:
        assert False


def test_device_list_no_devices(capsys, monkeypatch):
    monkeypatch.setattr(device, "all_devices", lambda: [])
    with exits_with_code(0):
        cli.run("devices".split())
    snapshot = capsys.readouterr()
    assert ("No connected CircuitPython devices") in snapshot.out


def contains_ordered_substrings(string: str, substrs: list[str]) -> bool:
    """Checks if the input string contains all of the requested substrings in order."""
    pattern = ".+".join(re.escape(s) for s in substrs)
    # Without DOTALL, '.' does not match across lines
    return re.search(pattern, string, flags=re.DOTALL) is not None


def test_device_list_multiple_devices(capsys, monkeypatch):
    device_a = device.Device("va", "ma", "sa")
    monkeypatch.setattr(device_a, "get_mountpoint", lambda: Path("/mount_a"))
    device_a.partition_path = Path("/partition_a")

    device_b = device.Device("vb", "mb", "sb")
    monkeypatch.setattr(device_b, "get_mountpoint", lambda: Path("/mount_b"))
    device_b.serial_path = Path("/serial_b")

    monkeypatch.setattr(device, "all_devices", lambda: [device_a, device_b])
    with exits_with_code(0):
        cli.run("devices".split())
    snapshot = capsys.readouterr()
    assert contains_ordered_substrings(
        snapshot.out,
        ["va", "ma", "sa", "/partition_a", "None", "/mount_a"]
        + ["vb", "mb", "sb", "None", "/serial_b", "/mount_b"],
    )
