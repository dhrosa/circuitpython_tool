from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..render import TableFields, pretty_datetime, rich_renderable_as_table
from . import partition
from .udev import UsbDevice


@rich_renderable_as_table
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

    @classmethod
    def __table_fields__(cls) -> TableFields:
        yield "Vendor", lambda d: d.vendor
        yield "Model", lambda d: d.model
        yield "Serial", lambda d: d.serial
        yield "Partition Path", lambda d: d.partition_path
        yield "Mountpoint", lambda d: d.get_mountpoint()
        yield "Connection Time", lambda d: pretty_datetime(d.connection_time)
