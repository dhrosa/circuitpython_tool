"""Device implementation for real CircuitPython devices."""

import logging
import os
import re
import termios
from dataclasses import dataclass, replace
from pathlib import Path

from . import partition
from .device import BootInfo, Device
from .udev import UsbDevice

logger = logging.getLogger(__name__)


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

        @dataclass(frozen=True)
        class Key:
            vendor_id: str
            model_id: str
            serial: str

            @staticmethod
            def from_usb_device(usb_device: UsbDevice) -> "Key":
                return Key(usb_device.vendor_id, usb_device.model_id, usb_device.serial)

        devices: dict[Key, RealDevice] = {}
        usb_devices = UsbDevice.all()

        # Find CIRCUITPY partition devices.
        for usb_device in usb_devices:
            if usb_device.partition_label != "CIRCUITPY":
                continue
            device = RealDevice(
                vendor=usb_device.vendor,
                model=usb_device.model,
                serial=usb_device.serial,
                partition_path=usb_device.path,
            )
            devices[Key.from_usb_device(usb_device)] = device

        # Find corresponding serial devices.
        for usb_device in usb_devices:
            if not usb_device.is_tty:
                continue
            key = Key.from_usb_device(usb_device)
            if key not in devices:
                continue
            # Take the descriptor strings from the serial device preferentially.
            # In my experience with the Raspberry Pi Pico, these strings are
            # more descriptive too.
            devices[key] = replace(
                devices[key],
                vendor=usb_device.vendor,
                model=usb_device.model,
                serial=usb_device.serial,
                serial_path=usb_device.path,
            )

        return set(devices.values())
