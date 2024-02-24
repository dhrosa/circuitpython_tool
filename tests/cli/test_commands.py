import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, TypeAlias

import pytest
import rich

from circuitpython_tool.cli import commands
from circuitpython_tool.hw import FakeDevice, devices_to_toml

CaptureFixture: TypeAlias = pytest.CaptureFixture[str]
MonkeyPatch: TypeAlias = pytest.MonkeyPatch


@pytest.fixture(autouse=True)
def disable_wrapping() -> None:
    """Prevents line wrapping in rich output."""
    rich.reconfigure(width=1000)


class CliRunner:
    """Fixture class for executing our CLI while automatically handling fake device creation."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.fake_devices: list[FakeDevice] = []

    def run(self, args_str: str) -> None:
        """Execute main, automatically filling in fake device information."""
        fake_config_path = self.base_path / "fake_devices.toml"
        fake_config_path.write_text(devices_to_toml(self.fake_devices))

        args = [
            "--fake-device-config",
            fake_config_path,
            *args_str.split(),
        ]
        commands.main(args)

    def add_device(self, *args: Any, **kwargs: Any) -> None:
        """Create and add a new FakeDevice.

        All arguments are forwarded to FakeDevice()."""
        self.fake_devices.append(FakeDevice(*args, **kwargs))


@pytest.fixture
def cli(tmp_path: Path) -> Iterator[CliRunner]:
    yield CliRunner(tmp_path)


@contextmanager
def exits_with_code(code: int) -> Iterator[None]:
    try:
        yield
    except SystemExit as exit:
        assert exit.code == code
    else:
        assert False


def test_subcommands() -> None:
    assert set(commands.main.commands.keys()) == {
        "clean",
        "completion",
        "connect",
        "devices",
        "mount",
        "uf2",
        "unmount",
        "upload",
    }


def test_device_list_no_devices(capsys: CaptureFixture, cli: CliRunner) -> None:
    with exits_with_code(0):
        cli.run("devices")
    snapshot = capsys.readouterr()
    assert ("No connected CircuitPython devices") in snapshot.out


def contains_ordered_substrings(string: str, substrs: list[str]) -> bool:
    """Checks if the input string contains all of the requested substrings in order."""
    pattern = ".+".join(re.escape(s) for s in substrs)
    # Without DOTALL, '.' does not match across lines
    return re.search(pattern, string, flags=re.DOTALL) is not None


def test_device_list_multiple_devices(capsys: CaptureFixture, cli: CliRunner) -> None:
    cli.add_device(
        "va",
        "ma",
        "sa",
        partition_path="/partition_a",
        mountpoint="/mount_a",
    )
    cli.add_device(
        "vb", "mb", "sb", partition_path="/partition_b", serial_path="/serial_b"
    )
    with exits_with_code(0):
        cli.run("devices")
    snapshot = capsys.readouterr()
    assert contains_ordered_substrings(
        snapshot.out,
        ["va", "ma", "sa", "/partition_a", "None", "/mount_a"]
        + ["vb", "mb", "sb", "/partition_b", "/serial_b", "None"],
    )


def test_device_list_query(capsys: CaptureFixture, cli: CliRunner) -> None:
    cli.add_device("va", "ma", "sa", Path("/partition1"))
    cli.add_device("vb", "mb", "sb", Path("/partition2"))
    with exits_with_code(0):
        cli.run("devices va:ma:")
    out = capsys.readouterr().out
    assert contains_ordered_substrings(out, ["va", "ma", "sa", "/partition1"])
    assert "vb" not in out
    assert "mb" not in out
    assert "sb" not in out


def test_connect(
    capsys: CaptureFixture,
    monkeypatch: MonkeyPatch,
    cli: CliRunner,
) -> None:
    # Intercept calls to execlp.
    exec_args: list[str] = []

    def fake_exec(*args: str) -> None:
        nonlocal exec_args
        exec_args = list(args)

    monkeypatch.setattr(commands, "execlp", fake_exec)

    cli.add_device("vv", "mm", "ss", "/partition", serial_path="/serial_path")
    with exits_with_code(0):
        cli.run("connect vv:mm:ss")

    assert exec_args == ["minicom", "minicom", "-D", "/serial_path"]


def test_device_save_fake_devices(tmp_path: Path, cli: CliRunner) -> None:
    cli.add_device("va", "ma", "sa", Path("/partition1"))
    cli.add_device("vb", "mb", "sb", Path("/partition2"))

    new_fake_config = tmp_path / "new_fake.toml"
    with exits_with_code(0):
        cli.run(f"devices --save {new_fake_config}")

    assert FakeDevice.all(new_fake_config) == {
        FakeDevice("va", "ma", "sa", Path("/partition1")),
        FakeDevice("vb", "mb", "sb", Path("/partition2")),
    }
