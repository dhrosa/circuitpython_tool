"""CircuitPython devices abstrations."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..render import TableFields, pretty_datetime, rich_renderable_as_table


@dataclass(frozen=True)
class BootInfo:
    version: str
    """Version of CircuitPython running on the board."""

    board_id: str
    """CircuitPython board identifier."""


@rich_renderable_as_table
@dataclass(frozen=True)
class Device:
    """A CircuitPython composite USB device."""

    vendor: str
    model: str
    serial: str

    # Path to partition device.
    partition_path: Path

    # Path to serial device.
    serial_path: Path | None = None

    @property
    def key(self) -> tuple[str, str, str]:
        """Unique and sortable identifier for this device."""
        return (self.vendor, self.model, self.serial)

    @property
    def connection_time(self) -> datetime:
        """The timestamp at which the device was connected to the system."""
        if not self.partition_path.exists():
            return datetime.fromtimestamp(0)
        return datetime.fromtimestamp(self.partition_path.stat().st_mtime)

    def get_mountpoint(self) -> Path | None:
        """Find mountpoint. Returns None if not mounted."""
        raise NotImplementedError()

    def mount_if_needed(self) -> Path:
        """Mounts the partition device if needed, and returns the mountpoint."""
        raise NotImplementedError

    def unmount_if_needed(self) -> None:
        """Unmounts the partition device if needed."""
        raise NotImplementedError

    def uf2_enter(self) -> None:
        """Restart device into the UF2 bootloader."""
        raise NotImplementedError

    def get_boot_info(self) -> BootInfo:
        """Lookup the adafruit board ID."""
        raise NotImplementedError()

    @classmethod
    def __table_fields__(cls) -> TableFields:
        yield "Vendor", lambda d: d.vendor
        yield "Model", lambda d: d.model
        yield "Serial", lambda d: d.serial
        yield "Partition Path", lambda d: d.partition_path
        yield "Serial Path", lambda d: d.serial_path
        yield "Mountpoint", lambda d: d.get_mountpoint()
        yield "Connection Time", lambda d: pretty_datetime(d.connection_time)
