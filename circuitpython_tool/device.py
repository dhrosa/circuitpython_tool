import logging
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from sys import exit
from typing import Self

logger = logging.getLogger(__name__)


def run(command: str) -> str:
    """Execute command and return its stdout output."""
    process = subprocess.run(shlex.split(command), capture_output=True, text=True)
    try:
        process.check_returncode()
    except subprocess.CalledProcessError:
        logger.error(f"Command:\n{command}\nExited with status {process.returncode}")
        if process.stdout:
            logger.error(f"stdout:\n{process.stdout}")
        if process.stderr:
            logger.error(f"stderr:\n{process.stderr}")
        raise
    return process.stdout


@dataclass
class Query:
    """Filter criteria for selecting a CircuitPython device."""

    vendor: str
    model: str
    serial: str

    class ParseError(ValueError):
        pass

    @staticmethod
    def parse(value: str) -> Self:
        if not value:
            return Query("", "", "")
        parts = value.split(":")
        if (count := len(parts)) != 3:
            raise Query.ParseError(
                f"Expected 3 query components. Instead found {count}."
            )
        return Query(*parts)

    def as_str(self) -> str:
        return f"{self.vendor}:{self.model}:{self.serial}"

    def matches(self, device):
        """Whether this device is matched by the query."""
        return all(
            (
                self.vendor in device.vendor,
                self.model in device.model,
                self.serial in device.serial,
            )
        )


@dataclass
class Device:
    """A CircuitPython composite USB device."""

    vendor: str
    model: str
    serial: str

    # Path to partition device.
    partition_path: Path = None

    # Path to serial device.
    serial_path: Path = None

    def get_mountpoint(self):
        """Find mountpoint. Returns empty string if not mounted."""
        command = f"lsblk {self.partition_path} --output mountpoint --noheadings"
        return run(command).strip()

    def mount_if_needed(self):
        """Mounts the partition device if needed, and returns the mountpoint."""
        mountpoint = self.get_mountpoint()
        if mountpoint:
            return mountpoint
        partition_path = self.partition_path
        command = f"udisksctl mount --block-device {partition_path} --options noatime"
        mount_stdout = run(command)
        logger.info(f"udisksctl: {mount_stdout}")
        mountpoint = self.get_mountpoint()
        if mountpoint:
            return mountpoint
        exit(f"{partition_path} somehow not mounted.")


def get_device_info(path):
    """
    Extract device attributes from udevadm.

    Returns None if the device is not a USB device.
    """
    info = {}
    command = f"udevadm info --query=property --name {path}"
    for line in run(command).splitlines():
        key, value = line.split("=", maxsplit=1)
        info[key] = value
    if info.get("ID_BUS", None) != "usb":
        return None
    return info


def all_devices():
    """Finds all USB CircuitPython devices."""

    devices = []

    def find_or_add_device(info):
        vendor = info["ID_USB_VENDOR"]
        model = info["ID_USB_MODEL"]
        serial = info["ID_USB_SERIAL_SHORT"]

        for device in devices:
            if (
                device.vendor == vendor
                and device.model == model
                and device.serial == serial
            ):
                return device
        device = Device(vendor, model, serial)
        devices.append(device)
        return device

    # Find CIRCUITPY partition devices.
    for path in Path("/dev/disk/by-id/").iterdir():
        info = get_device_info(path)
        if (
            info is None
            or info["DEVTYPE"] != "partition"
            or info["ID_FS_LABEL"] != "CIRCUITPY"
        ):
            continue
        device = find_or_add_device(info)
        device.partition_path = path.resolve()

    # Find serial devices.

    # Parent directory might not exist if there are no attached serial devices.
    serial_dir = Path("/dev/serial/by-id/")
    if not serial_dir.exists():
        logging.info("No serial devices found.")
        return []
    for path in serial_dir.iterdir():
        info = get_device_info(path)
        if info is None:
            continue
        device = find_or_add_device(info)
        device.serial_path = path.resolve()

    return devices


def matching_devices(query: Query):
    return [d for d in all_devices() if query.matches(d)]
