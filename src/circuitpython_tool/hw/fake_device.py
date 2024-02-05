"""Fake Device implementation for testing and demos."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import tomlkit
from tomlkit.items import Table

from .device import Device


@dataclass(frozen=True)
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
    def all(toml: str | Path) -> set["FakeDevice"]:
        """Load FakeDevice objects from a TOML file."""
        if isinstance(toml, Path):
            toml = toml.read_text()
        document = tomlkit.loads(toml)
        tables = document.get("devices", tomlkit.aot())
        assert isinstance(tables, list)
        return {FakeDevice.from_toml(t) for t in tables}

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


def to_toml(devices: Iterable[Device]) -> str:
    """Save arbitrary Device objects to a TOML file."""
    doc = tomlkit.document()
    devices_array = tomlkit.aot()
    for d in sorted(devices, key=lambda d: d.key):
        fake = FakeDevice(
            vendor=d.vendor,
            model=d.model,
            serial=d.serial,
            mountpoint=d.get_mountpoint(),
            partition_path=d.partition_path,
            serial_path=d.serial_path,
        )
        devices_array.append(fake.to_toml())
    doc["devices"] = devices_array
    return tomlkit.dumps(doc)
