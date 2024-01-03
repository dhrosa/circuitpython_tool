from pathlib import Path

import pytest

from circuitpython_tool.fake_device import FakeDevice, all_devices, to_toml


def test_empty_str() -> None:
    assert all_devices("") == []


def test_required_fields() -> None:
    toml = """
[[devices]]
vendor = "a"
model = "b"
serial = "c"

[[devices]]
vendor = "d"
model = "e"
serial = "f"
    """
    assert all_devices(toml) == [FakeDevice("a", "b", "c"), FakeDevice("d", "e", "f")]


def test_missing_required_fields() -> None:
    toml = """
[[devices]]
vendor = "v"
# model = "m"
serial = "s"
   """
    with pytest.raises(KeyError) as exception_info:
        all_devices(toml)
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
    assert all_devices(toml) == [
        FakeDevice(
            "v",
            "m",
            "s",
            serial_path=Path("/serial"),
            partition_path=Path("/partition"),
            mountpoint=Path("/mount"),
        ),
    ]


def test_file_read(tmp_path: Path) -> None:
    toml = """
[[devices]]
vendor = "v"
model = "m"
serial = "s"
      """
    file_path = tmp_path / "devices.toml"
    file_path.write_text(toml)
    assert all_devices(file_path) == [FakeDevice("v", "m", "s")]


def test_to_toml() -> None:
    original_devices = [
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
        FakeDevice("vb", "mb", "sb"),
    ]

    toml = to_toml(original_devices)
    devices = all_devices(toml)

    assert devices == original_devices
