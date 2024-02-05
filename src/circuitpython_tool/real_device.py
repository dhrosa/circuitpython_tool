"""Device implementation for real CircuitPython devices."""

import logging
import os
import shlex
import subprocess
import termios
from dataclasses import replace
from pathlib import Path
from typing import TypeAlias

from .device import Device

logger = logging.getLogger(__name__)

SERIAL_DIR = Path("/dev/serial/by-id")
"""Contains all serial devices. Directory might not exist if none are connected."""

PARTITION_DIR = Path("/dev/disk/by-id")
"""Contains all partition devices on the system."""


class RealDevice(Device):
    def get_mountpoint(self) -> Path | None:
        if not self.partition_path:
            return None
        command = f"lsblk {self.partition_path} --output mountpoint --noheadings"
        out = _run(command).strip()
        if not out:
            return None
        return Path(out)

    def mount_if_needed(self) -> Path:
        mountpoint = self.get_mountpoint()
        if mountpoint:
            return mountpoint
        partition_path = self.partition_path
        command = f"udisksctl mount --block-device {partition_path} --options noatime"
        mount_stdout = _run(command)
        logger.info(f"udisksctl: {mount_stdout}")
        mountpoint = self.get_mountpoint()
        if mountpoint:
            return mountpoint
        exit(f"{partition_path} somehow not mounted.")

    def unmount_if_needed(self) -> None:
        if not self.get_mountpoint():
            return
        command = f"udisksctl unmount --block-device {self.partition_path}"
        unmount_stdout = _run(command)
        logger.info(f"udisksctl: {unmount_stdout}")

    def uf2_enter(self) -> None:
        # RP2040-based builds enter the UF2 bootloader when the USB CDC
        # connection is set to a baudrate of 1200.
        if not self.serial_path:
            raise ValueError("No serial path associated with device: {self}")
        try:
            fd = os.open(self.serial_path, os.O_RDWR)
            attributes = termios.tcgetattr(fd)
            # Input and output speeds.
            attributes[4:6] = (termios.B1200, termios.B1200)
            termios.tcsetattr(fd, termios.TCSANOW, attributes)
        finally:
            os.close(fd)


def all_devices() -> set[RealDevice]:
    """Finds all USB CircuitPython devices."""

    # Maps (vendor, model, serial) to RealDevice instances.
    Key: TypeAlias = tuple[str, str, str]
    devices: dict[Key, RealDevice] = {}

    def key(d: RealDevice) -> Key:
        return (d.vendor, d.model, d.serial)

    def find_or_add_device(properties: dict[str, str]) -> RealDevice:
        device = RealDevice(
            vendor=properties["ID_USB_VENDOR"],
            model=properties["ID_USB_MODEL"],
            serial=properties["ID_USB_SERIAL_SHORT"],
        )
        return devices.setdefault(key(device), device)

    # Find CIRCUITPY partition devices.
    for path in PARTITION_DIR.iterdir():
        properties = usb_device_properties(path)
        if (
            properties is None
            or properties["DEVTYPE"] != "partition"
            or properties["ID_FS_LABEL"] != "CIRCUITPY"
        ):
            continue
        device = find_or_add_device(properties)
        devices[key(device)] = replace(device, partition_path=path)

    # Find serial devices.

    # Parent directory might not exist if there are no attached serial devices.
    if SERIAL_DIR.exists():
        for path in SERIAL_DIR.iterdir():
            properties = usb_device_properties(path)
            if properties is None:
                continue
            device = find_or_add_device(properties)
            devices[key(device)] = replace(device, serial_path=path)
    else:
        logging.info("No serial devices found.")

    return set(devices.values())


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
    return _run(f"udevadm info --query=property --name {path}")


def _run(command: str) -> str:
    """Execute command and return its stdout output."""
    # TODO(dhrosa): Debug logs of command executions.
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
