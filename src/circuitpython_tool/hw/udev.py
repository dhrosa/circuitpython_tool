from pathlib import Path

from .shell import run


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
    return run(f"udevadm info --query=property --name {path}")
