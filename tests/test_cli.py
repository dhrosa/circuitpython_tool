import re
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, TypeAlias

import pytest

from circuitpython_tool import cli, device
from circuitpython_tool.config import ConfigStorage

CaptureFixture: TypeAlias = pytest.CaptureFixture[str]
MonkeyPatch: TypeAlias = pytest.MonkeyPatch


@pytest.fixture
def config_storage(tmp_path: Path) -> ConfigStorage:
    return ConfigStorage(tmp_path / "config.toml")


@contextmanager
def exits_with_code(code: int) -> Generator[None, None, None]:
    try:
        yield
    except SystemExit as exit:
        assert exit.code == code
    else:
        assert False


def test_device_list_no_devices(
    capsys: CaptureFixture, monkeypatch: MonkeyPatch
) -> None:
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


def test_device_list_multiple_devices(
    capsys: CaptureFixture, monkeypatch: MonkeyPatch
) -> None:
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


def test_device_list_query(capsys: CaptureFixture, monkeypatch: MonkeyPatch) -> None:
    device_a = device.Device("va", "ma", "sa")
    monkeypatch.setattr(device_a, "get_mountpoint", lambda: Path("/mount_a"))

    device_b = device.Device("vb", "mb", "sb")
    monkeypatch.setattr(device_b, "get_mountpoint", lambda: Path("/mount_b"))

    monkeypatch.setattr(device, "all_devices", lambda: [device_a, device_b])
    with exits_with_code(0):
        cli.run("devices va:ma:".split())
    out = capsys.readouterr().out
    assert contains_ordered_substrings(out, ["va", "ma", "sa", "/mount_a"])
    assert "vb" not in out
    assert "mb" not in out
    assert "sb" not in out
    assert "/mount_b" not in out


def test_label_add(capsys: CaptureFixture, config_storage: ConfigStorage) -> None:
    # Add label_a
    with exits_with_code(0):
        cli.run(f"--config {config_storage.path} label add label_a va:ma:sa".split())
    assert "Label label_a added" in capsys.readouterr().out

    # Should be in list output
    with exits_with_code(0):
        cli.run(f"--config {config_storage.path} label list".split())
    assert contains_ordered_substrings(capsys.readouterr().out, ["label_a", "va:ma:sa"])


def test_connect(
    capsys: CaptureFixture, monkeypatch: MonkeyPatch, config_storage: ConfigStorage
) -> None:
    exec_args: list[str] = []

    def fake_exec(*args: str) -> None:
        nonlocal exec_args
        exec_args = list(args)

    monkeypatch.setattr(cli, "execlp", fake_exec)

    dev = device.Device("vv", "mm", "ss")
    dev.serial_path = Path("/serial_path")
    monkeypatch.setattr(dev, "get_mountpoint", lambda: "/mount")
    monkeypatch.setattr("circuitpython_tool.cli.all_devices", lambda: [dev])
    monkeypatch.setattr("circuitpython_tool.device.all_devices", lambda: [dev])

    with exits_with_code(0):
        cli.run(f"--config {config_storage.path} label add label_a vv:mm:ss".split())

    with exits_with_code(0):
        cli.run(f"--config {config_storage.path} devices".split())

    with exits_with_code(0):
        cli.run(f"--config {config_storage.path} connect label_a".split())

    assert exec_args == ["minicom", "minicom", "-D", "/serial_path"]
