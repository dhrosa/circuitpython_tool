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


def ordered_substrings_re(substrs: list[str]) -> re.Pattern:
    """Regex that matches strings containing all of the requested substrings in order."""
    pattern_str = ".+".join(re.escape(s) for s in substrs)
    # Without DOTALL, '.' does not match across lines
    return re.compile(pattern_str, flags=re.DOTALL)


def test_device_list_multiple_devices(capsys, monkeypatch):
    device_a = device.Device("vendor_a", "model_a", "serial_a")
    monkeypatch.setattr(device_a, "get_mountpoint", lambda: Path("/mount_a"))
    device_a.partition_path = Path("/partition_a")

    device_b = device.Device("vendor_b", "model_b", "serial_b")
    monkeypatch.setattr(device_b, "get_mountpoint", lambda: Path("/mount_b"))
    device_b.serial_path = Path("/serial_b")

    monkeypatch.setattr(device, "all_devices", lambda: [device_a, device_b])
    with exits_with_code(0):
        cli.run("devices".split())
    snapshot = capsys.readouterr()
    pattern = ordered_substrings_re(
        ["vendor_a", "model_a", "serial_a", "/partition_a", "None", "/mount_a"]
        + ["vendor_b", "model_b", "serial_b", "None", "/serial_b", "/mount_b"]
    )
    assert pattern.search(snapshot.out)
