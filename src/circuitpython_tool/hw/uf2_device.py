from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import partition
from .udev import UsbDevice


@dataclass(frozen=True)
class Uf2Device:
    """A device in UF2 bootloader mode."""

    vendor: str
    model: str
    serial: str

    partition_path: Path

    @property
    def connection_time(self) -> datetime:
        """The timestamp at which the device was connected to the system."""
        return datetime.fromtimestamp(self.partition_path.stat().st_mtime)

    def get_mountpoint(self) -> Path | None:
        return partition.mountpoint(self.partition_path)

    def mount_if_needed(self) -> Path:
        return partition.mount_if_needed(self.partition_path)

    def unmount_if_needed(self) -> None:
        partition.unmount_if_needed(self.partition_path)

    @staticmethod
    def all() -> set["Uf2Device"]:
        """Find all devices waiting in UF2 bootloader mode."""
        devices: set[Uf2Device] = set()
        for usb_device in UsbDevice.all():
            if usb_device.partition_label != "RPI-RP2":
                continue
            devices.add(
                Uf2Device(
                    vendor=usb_device.vendor,
                    model=usb_device.model,
                    serial=usb_device.serial,
                    partition_path=usb_device.path.resolve(),
                )
            )
        return devices
