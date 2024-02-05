"""CircuitPython devices abstrations."""

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Device:
    """A CircuitPython composite USB device."""

    vendor: str
    model: str
    serial: str

    # Path to partition device.
    partition_path: Path | None = None

    # Path to serial device.
    serial_path: Path | None = None

    @property
    def key(self) -> tuple[str, str, str]:
        """Unique and sortable identifier for this device."""
        return (self.vendor, self.model, self.serial)

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
