import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Device:
    """A CircuitPython composite USB device."""

    vendor: str
    model: str
    serial: str

    # Path to partition device.
    partition_path: Path | None = None

    # Path to serial device.
    serial_path: Path | None = None

    def get_mountpoint(self) -> Path | None:
        """Find mountpoint. Returns None if not mounted."""
        raise NotImplementedError()

    def mount_if_needed(self) -> Path:
        """Mounts the partition device if needed, and returns the mountpoint."""
        raise NotImplementedError
