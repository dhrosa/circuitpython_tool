from dataclasses import dataclass
from pathlib import Path

from .partition import PARTITION_DIR
from .udev import usb_device_properties


@dataclass(frozen=True)
class Uf2Device:
    """A device in UF2 bootloader mode."""

    vendor: str
    model: str
    serial: str

    partition_path: Path

    @staticmethod
    def all() -> set["Uf2Device"]:
        """Find all devices waiting in UF2 bootloader mode."""
        devices: set[Uf2Device] = set()
        for path in PARTITION_DIR.iterdir():
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
                    partition_path=path,
                )
            )
        return devices
