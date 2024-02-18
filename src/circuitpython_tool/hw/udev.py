from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ..iter import as_list
from .shell import run


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

    partition_label: str | None = None
    """If this is a partition device, the filesystem label."""

    is_tty: bool = False
    """True if this is a serial terminal."""

    @as_list
    @staticmethod
    def all() -> Iterator["UsbDevice"]:
        """List of all attached USB devices."""
        # Entries have one blank line between them.
        for entry in udevadm_export_db().rstrip().split("\n\n"):
            properties = parse_properties(entry)
            if properties.get("ID_BUS") != "usb":
                continue
            # DEVPATH names don't work with 'lsblk', so we use DEVNAME
            if not (devname := properties.get("DEVNAME")):
                continue
            yield UsbDevice(
                path=Path(devname),
                vendor=properties["ID_USB_VENDOR"],
                model=properties["ID_USB_MODEL"],
                serial=(
                    properties.get("ID_USB_SERIAL_SHORT") or properties["ID_USB_SERIAL"]
                ),
                is_tty=properties["SUBSYSTEM"] == "tty",
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
