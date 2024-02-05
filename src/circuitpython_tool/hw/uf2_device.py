from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import partition
from .udev import usb_device_properties


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
        for path in partition.PARTITION_DIR.iterdir():
            properties = usb_device_properties(path)
            if (
                properties is None
                or properties["DEVTYPE"] != "partition"
                or properties["ID_FS_LABEL"] != "RPI-RP2"
            ):
                continue
            devices.add(
                Uf2Device(
                    vendor=properties["ID_USB_VENDOR"],
                    model=properties["ID_USB_MODEL"],
                    serial=properties["ID_USB_SERIAL_SHORT"],
                    partition_path=path.resolve(),
                )
            )
        return devices
