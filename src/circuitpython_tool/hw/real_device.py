"""Device implementation for real CircuitPython devices."""

import logging
import os
import re
import termios
from dataclasses import replace
from pathlib import Path

from . import partition
from .device import BootInfo, Device
from .partition import PARTITION_DIR
from .udev import usb_device_properties

logger = logging.getLogger(__name__)

SERIAL_DIR = Path("/dev/serial/by-id")
"""Contains all serial devices. Directory might not exist if none are connected."""


class RealDevice(Device):
    def get_mountpoint(self) -> Path | None:
        return partition.mountpoint(self.partition_path)

    def mount_if_needed(self) -> Path:
        return partition.mount_if_needed(self.partition_path)

    def unmount_if_needed(self) -> None:
        partition.unmount_if_needed(self.partition_path)

    def uf2_enter(self) -> None:
        # RP2040-based builds enter the UF2 bootloader when the USB CDC
        # connection is set to a baudrate of 1200.
        if not self.serial_path:
            raise ValueError("No serial path associated with device: {self}")
        fd = os.open(self.serial_path, os.O_RDWR)
        try:
            logging.info(
                f"Triggering bootloader restart by setting baud rate on {self.serial_path} to 1200."
            )
            attributes = termios.tcgetattr(fd)
            # Input and output speeds.
            attributes[4:6] = (termios.B1200, termios.B1200)
            termios.tcsetattr(fd, termios.TCSANOW, attributes)
        finally:
            os.close(fd)
        logging.info(f"Closed {self.serial_path}")

    def get_boot_info(self) -> BootInfo:
        with partition.temporarily_mount(self.partition_path) as mountpoint:
            boot_out = (mountpoint / "boot_out.txt").read_text()
        [version_line, board_id_line, *rest] = boot_out.splitlines()
        version_match = re.match(r"^Adafruit CircuitPython ([^\s]*)", version_line)
        if not version_match:
            raise ValueError(f"Unable to parse version info from line: {version_line}")
        board_id_match = re.match(r"^Board ID:([^\s]*)", board_id_line)
        if not board_id_match:
            raise ValueError(f"Unable to parse board id from line: {board_id_line}")
        return BootInfo(version_match[1], board_id_match[1])

    @staticmethod
    def all() -> set["RealDevice"]:
        """Finds all USB CircuitPython devices."""

        # Maps (vendor, model, serial) to RealDevice instances.
        devices: dict[tuple[str, str, str], RealDevice] = {}

        def vendor(properties: dict[str, str]) -> str:
            return properties["ID_USB_VENDOR"]

        def model(properties: dict[str, str]) -> str:
            return properties["ID_USB_MODEL"]

        def serial(properties: dict[str, str]) -> str:
            return properties["ID_USB_SERIAL_SHORT"]

        # Find CIRCUITPY partition devices.
        for path in PARTITION_DIR.iterdir():
            properties = usb_device_properties(path)
            if (
                properties is None
                or properties["DEVTYPE"] != "partition"
                or properties["ID_FS_LABEL"] != "CIRCUITPY"
            ):
                continue
            device = RealDevice(
                vendor=vendor(properties),
                model=model(properties),
                serial=serial(properties),
                partition_path=path.resolve(),
            )
            devices[device.key] = device

        # Find corresponding serial devices.

        # Parent directory might not exist if there are no attached serial devices.
        if SERIAL_DIR.exists():
            for path in SERIAL_DIR.iterdir():
                properties = usb_device_properties(path)
                if properties is None:
                    continue
                key = vendor(properties), model(properties), serial(properties)
                if key not in devices:
                    continue
                devices[key] = replace(devices[key], serial_path=path.resolve())
        else:
            logging.info("No serial devices found.")

        return set(devices.values())
