import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, TypeAlias

import pytest

import circuitpython_tool.cli.cli as cli_module
from circuitpython_tool.hw.fake_device import FakeDevice, to_toml

CaptureFixture: TypeAlias = pytest.CaptureFixture[str]
MonkeyPatch: TypeAlias = pytest.MonkeyPatch


class CliRunner:
    """Fixture class for executing our CLI while automatically handling fake device creation."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.fake_devices: list[FakeDevice] = []

    def run(self, args_str: str) -> None:
        """Execute main, automatically filling in fake device information."""
        fake_config_path = self.base_path / "fake_devices.toml"
        fake_config_path.write_text(to_toml(self.fake_devices))

        args = [
            "--fake-device-config",
            fake_config_path,
            "--config",
            self.base_path / "config.toml",
            *args_str.split(),
        ]
        cli_module.main(args)

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
    cli.add_device("vb", "mb", "sb", serial_path="/serial_b")
    with exits_with_code(0):
        cli.run("devices")
    snapshot = capsys.readouterr()
    assert contains_ordered_substrings(
        snapshot.out,
        ["va", "ma", "sa", "/partition_a", "None", "/mount_a"]
        + ["vb", "mb", "sb", "None", "/serial_b", "None"],
    )


def test_device_list_query(capsys: CaptureFixture, cli: CliRunner) -> None:
    cli.add_device("va", "ma", "sa")
    cli.add_device("vb", "mb", "sb")
    with exits_with_code(0):
        cli.run("devices va:ma:")
    out = capsys.readouterr().out
    assert contains_ordered_substrings(out, ["va", "ma", "sa"])
    assert "vb" not in out
    assert "mb" not in out
    assert "sb" not in out


def test_label_add(capsys: CaptureFixture, cli: CliRunner) -> None:
    # Add label_a
    with exits_with_code(0):
        cli.run("label add label_a va:ma:sa")
    assert "Label label_a added" in capsys.readouterr().out

    # Should be in list output
    with exits_with_code(0):
        cli.run("label list")
    assert contains_ordered_substrings(capsys.readouterr().out, ["label_a", "va:ma:sa"])


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

    monkeypatch.setattr(cli_module, "execlp", fake_exec)

    cli.add_device("vv", "mm", "ss", serial_path="/serial_path")
    with exits_with_code(0):
        cli.run("label add label_a vv:mm:ss")

    with exits_with_code(0):
        cli.run("devices")

    with exits_with_code(0):
        cli.run("connect label_a")

    assert exec_args == ["minicom", "minicom", "-D", "/serial_path"]


def test_device_save_fake_devices(tmp_path: Path, cli: CliRunner) -> None:
    cli.add_device("va", "ma", "sa")
    cli.add_device("vb", "mb", "sb")

    new_fake_config = tmp_path / "new_fake.toml"
    with exits_with_code(0):
        cli.run(f"devices --save {new_fake_config}")

    assert FakeDevice.all(new_fake_config) == {
        FakeDevice("va", "ma", "sa"),
        FakeDevice("vb", "mb", "sb"),
    }
