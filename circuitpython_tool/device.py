from dataclasses import dataclass
import subprocess
from pathlib import Path
from sys import exit


def run(args):
    """Execute command and return its stdout output."""
    process = subprocess.run(args, capture_output=True, text=True)
    try:
        process.check_returncode()
    except subprocess.CalledProcessError as e:
        print(f"{args[0]} exited with status {process.returncode}")
        if process.stdout:
            print(f"stdout:\n{process.stdout}")
        if process.stderr:
            print(f"stderr:\n{process.stderr}")
        raise
    return process.stdout


@dataclass
class Device:
    """A CircuitPython composite USB device."""

    vendor: str
    model: str
    serial: str

    # Path to partition device.
    partition_path: str = None

    # Path to serial device.
    serial_path: str = None

    def get_mountpoint(self):
        """Find mountpoint. Returns empty string if not mounted."""
        args = f"lsblk {self.partition_path} --output mountpoint --noheadings".split()
        return run(args).strip()

    def mount_if_needed(self):
        """Mounts the partition device if needed, and returns the mountpoint."""
        mountpoint = self.get_mountpoint()
        if mountpoint:
            return mountpoint
        mount_stdout = run(
            f"udisksctl mount --block-device {self.partition_path} --options noatime".split()
        )
        print(f"udisksctl: {mount_stdout}")
        mountpoint = self.get_mountpoint(partition_path)
        if mountpoint:
            return mountpoint
        exit(f"{partition_path} somehow not mounted.")


def get_device_info(path):
    """
    Extract device attributes from udevadm.

    Returns None if the device is not a USB device.
    """
    info = {}
    args = f"udevadm info --query=property --name {path}".split()
    for line in run(args).splitlines():
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
        device.partition_path = str(path)

    # Find serial devices.
    for path in Path("/dev/serial/by-id/").iterdir():
        info = get_device_info(path)
        if info is None:
            continue
        device = find_or_add_device(info)
        device.serial_path = str(path)

    return devices
