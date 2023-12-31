from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import tomlkit
from tomlkit.items import Table

from .device import Device


@dataclass
class FakeDevice(Device):
    """Fake Device implementation for use in tests and demos."""

    mountpoint: Path | None = None

    def get_mountpoint(self) -> Path | None:
        return self.mountpoint

    def mount_if_needed(self) -> Path:
        path = self.get_mountpoint()
        assert path
        return path

    @staticmethod
    def from_toml(table: Table) -> "FakeDevice":
        def get(key: str) -> str:
            value = table[key]
            assert isinstance(value, str)
            return value

        def get_optional_path(key: str) -> Path | None:
            value = table.get(key)
            if isinstance(value, str):
                return Path(value)
            return value

        return FakeDevice(
            vendor=get("vendor"),
            model=get("model"),
            serial=get("serial"),
            partition_path=get_optional_path("partition_path"),
            serial_path=get_optional_path("serial_path"),
            mountpoint=get_optional_path("mountpoint"),
        )

    def to_toml(self) -> Table:
        table = tomlkit.table()
        table["vendor"] = self.vendor
        table["model"] = self.model
        table["serial"] = self.serial
        if self.mountpoint:
            table["mountpoint"] = str(self.mountpoint)
        if self.partition_path:
            table["partition_path"] = str(self.partition_path)
        if self.serial_path:
            table["serial_path"] = str(self.serial_path)
        return table


def all_devices(toml: str | Path) -> list[FakeDevice]:
    """Load FakeDevice objects from a TOML file."""
    if isinstance(toml, Path):
        toml = toml.read_text()
    document = tomlkit.loads(toml)
    tables = document.get("devices", tomlkit.aot())
    assert isinstance(tables, list)
    return [FakeDevice.from_toml(t) for t in tables]


def to_toml(devices: Sequence[FakeDevice]) -> str:
    doc = tomlkit.document()
    devices_array = tomlkit.aot()
    for d in devices:
        devices_array.append(d.to_toml())
    doc["devices"] = devices_array
    return tomlkit.dumps(doc)
