from collections.abc import Iterator
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from ..iter import as_list
from .shell import run

logger = getLogger(__name__)


def usb_device_properties(path: Path) -> dict[str, str] | None:
    """
    Extract device properties from udevadm.

    Returns None if the device is not a USB device.
    """
    properties = {}
    for line in udevadm_info(path).splitlines():
        key, value = line.split("=", maxsplit=1)
        properties[key] = value
    if properties.get("ID_BUS", None) != "usb":
        return None
    return properties


def udevadm_info(path: Path) -> str:
    """Uses `udevadm info` command to lookup device properties.

    Output consists of KEY=VALUE lines.

    Separated out for patching in unit tests.
    """
    return run(f"udevadm info --query=property --name {path}")


def udevadm_export_db() -> str:
    """Dump information on all attached devices.

    Separated out for patching in unit tests.

    Output format of udevadm documented at:
    https://man7.org/linux/man-pages/man8/udevadm.8.html#:~:text=Table%201.%20udevadm%20info%20output%20prefixes
    """
    return run("udevadm info --export-db")


@dataclass
class UsbDevice:
    """USB device properties from udev."""

    path: Path
    vendor: str
    model: str
    serial: str

    partition_label: str | None
    """If this is a partition device, the filesystem label."""

    @as_list
    @staticmethod
    def all() -> Iterator["UsbDevice"]:
        """List of all attached USB devices."""
        # Entries have one blank line between them.
        for entry in udevadm_export_db().rstrip().split("\n\n"):
            properties = parse_properties(entry)
            if properties.get("ID_BUS") != "usb":
                continue
            yield UsbDevice(
                path=Path(properties["DEVPATH"]),
                vendor=properties["ID_USB_VENDOR"],
                model=properties["ID_USB_MODEL"],
                serial=(
                    properties.get("ID_USB_SERIAL_SHORT") or properties["ID_USB_SERIAL"]
                ),
                partition_label=properties.get("ID_FS_LABEL"),
            )


def parse_properties(entry: str) -> dict[str, str]:
    """Parse device properties from a udev database entry."""
    properties: dict[str, str] = {}
    for original_line in entry.splitlines():
        # Only pay attention to device property lines (prefix "E:")
        line = original_line.removeprefix("E: ")
        if line == original_line:
            continue
        key, value = line.split("=", maxsplit=1)
        properties[key] = value
    return properties
