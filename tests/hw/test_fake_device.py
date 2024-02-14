from pathlib import Path

import pytest

from circuitpython_tool.hw import FakeDevice, devices_to_toml


def test_empty_str() -> None:
    assert FakeDevice.all("") == set()


def test_required_fields() -> None:
    toml = """
[[devices]]
vendor = "a"
model = "b"
serial = "c"
partition_path = "/partition1"

[[devices]]
vendor = "d"
model = "e"
serial = "f"
partition_path = "/partition2"
    """
    assert FakeDevice.all(toml) == {
        FakeDevice("a", "b", "c", Path("/partition1")),
        FakeDevice("d", "e", "f", Path("/partition2")),
    }


def test_missing_required_fields() -> None:
    toml = """
[[devices]]
vendor = "v"
# model = "m"
serial = "s"
partition_path = "/partition"
   """
    with pytest.raises(KeyError) as exception_info:
        FakeDevice.all(toml)
    assert "model" in str(exception_info.value)


def test_optional_fields() -> None:
    toml = """
[[devices]]
vendor = "v"
model = "m"
serial = "s"

serial_path = "/serial"
partition_path = "/partition"
mountpoint = "/mount"
   """
    assert FakeDevice.all(toml) == {
        FakeDevice(
            "v",
            "m",
            "s",
            serial_path=Path("/serial"),
            partition_path=Path("/partition"),
            mountpoint=Path("/mount"),
        ),
    }


def test_file_read(tmp_path: Path) -> None:
    toml = """
[[devices]]
vendor = "v"
model = "m"
serial = "s"
partition_path = "/partition"
      """
    file_path = tmp_path / "devices.toml"
    file_path.write_text(toml)
    assert FakeDevice.all(file_path) == {FakeDevice("v", "m", "s", Path("/partition"))}


def test_to_toml() -> None:
    original_devices = {
        # All fields set
        FakeDevice(
            "va",
            "ma",
            "sa",
            serial_path=Path("/serial"),
            partition_path=Path("/partition"),
            mountpoint=Path("/mount"),
        ),
        # Optional fields unset
        FakeDevice("vb", "mb", "sb", Path("/partition")),
    }

    toml = devices_to_toml(original_devices)
    devices = FakeDevice.all(toml)

    assert devices == original_devices
