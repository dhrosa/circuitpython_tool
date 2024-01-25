import logging
import shlex
import subprocess
from pathlib import Path

from .device import Device

logger = logging.getLogger(__name__)


def _run(command: str) -> str:
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


class RealDevice(Device):
    def get_mountpoint(self) -> Path | None:
        if self.partition_path is None:
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


def all_devices() -> list[RealDevice]:
    """Finds all USB CircuitPython devices."""
    devices: list[RealDevice] = []

    def find_or_add_device(info: dict[str, str]) -> RealDevice:
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
        device = RealDevice(vendor, model, serial)
        devices.append(device)
        return device

    # Find CIRCUITPY partition devices.
    for path in Path("/dev/disk/by-id/").iterdir():
        info = _get_device_info(path)
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
        info = _get_device_info(path)
        if info is None:
            continue
        device = find_or_add_device(info)
        device.serial_path = path.resolve()

    return devices


def _get_device_info(path: Path) -> dict[str, str] | None:
    """
    Extract device attributes from udevadm.

    Returns None if the device is not a USB device.
    """
    info = {}
    command = f"udevadm info --query=property --name {path}"
    for line in _run(command).splitlines():
        key, value = line.split("=", maxsplit=1)
        info[key] = value
    if info.get("ID_BUS", None) != "usb":
        return None
    return info
