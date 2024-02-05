"""Library for interacting with partition devices (e.g. /dev/sda1)."""

from logging import getLogger
from pathlib import Path

from .shell import run

logger = getLogger(__name__)

PARTITION_DIR = Path("/dev/disk/by-id")
"""Contains all partition devices on the system."""


def mountpoint(partition_path: Path) -> Path | None:
    """Find the mountpoint of the given partition device.

    Returns None if the device is not mounted."""
    if not partition_path:
        return None
    command = f"lsblk {partition_path} --output mountpoint --noheadings"
    out = run(command).strip()
    if not out:
        return None
    return Path(out)


def mount_if_needed(partition_path: Path) -> Path:
    """Mount the given device if needed and return the mountpoint."""
    existing_mountpoint = mountpoint(partition_path)
    if existing_mountpoint:
        return existing_mountpoint
    command = f"udisksctl mount --block-device {partition_path} --options noatime"
    mount_stdout = run(command)
    logger.info(f"udisksctl: {mount_stdout}")
    new_mountpoint = mountpoint(partition_path)
    if new_mountpoint:
        return new_mountpoint
    exit(f"{partition_path} somehow not mounted.")


def unmount_if_needed(partition_path: Path) -> None:
    """Unmount the given device if needed."""
    command = f"udisksctl unmount --block-device {partition_path}"
    unmount_stdout = run(command)
    logger.info(f"udisksctl: {unmount_stdout}")
