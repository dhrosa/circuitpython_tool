"""Device implementation for real CircuitPython devices."""

import logging
import os
import termios
from dataclasses import replace
from pathlib import Path

from . import partition
from .device import Device
from .partition import PARTITION_DIR
from .udev import usb_device_properties

logger = logging.getLogger(__name__)

SERIAL_DIR = Path("/dev/serial/by-id")
"""Contains all serial devices. Directory might not exist if none are connected."""


class RealDevice(Device):
    def get_mountpoint(self) -> Path | None:
        if not self.partition_path:
            return None
        return partition.mountpoint(self.partition_path)

    def mount_if_needed(self) -> Path:
        assert self.partition_path
        return partition.mount_if_needed(self.partition_path)

    def unmount_if_needed(self) -> None:
        assert self.partition_path
        partition.unmount_if_needed(self.partition_path)

    def uf2_enter(self) -> None:
        # RP2040-based builds enter the UF2 bootloader when the USB CDC
        # connection is set to a baudrate of 1200.
        if not self.serial_path:
            raise ValueError("No serial path associated with device: {self}")
        fd = os.open(self.serial_path, os.O_RDWR)
        try:
            attributes = termios.tcgetattr(fd)
            # Input and output speeds.
            attributes[4:6] = (termios.B1200, termios.B1200)
            termios.tcsetattr(fd, termios.TCSANOW, attributes)
        finally:
            os.close(fd)

    @staticmethod
    def all() -> set["RealDevice"]:
        """Finds all USB CircuitPython devices."""

        # Maps (vendor, model, serial) to RealDevice instances.
        devices: dict[tuple[str, str, str], RealDevice] = {}

        def find_or_add_device(properties: dict[str, str]) -> RealDevice:
            device = RealDevice(
                vendor=properties["ID_USB_VENDOR"],
                model=properties["ID_USB_MODEL"],
                serial=properties["ID_USB_SERIAL_SHORT"],
            )
            return devices.setdefault(device.key, device)

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
            devices[device.key] = replace(device, partition_path=path)

        # Find serial devices.

        # Parent directory might not exist if there are no attached serial devices.
        if SERIAL_DIR.exists():
            for path in SERIAL_DIR.iterdir():
                properties = usb_device_properties(path)
                if properties is None:
                    continue
                device = find_or_add_device(properties)
                devices[device.key] = replace(device, serial_path=path)
        else:
            logging.info("No serial devices found.")

        return set(devices.values())
