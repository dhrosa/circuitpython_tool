import subprocess
from pathlib import Path
import shutil
from sys import exit
from os import execlp
from functools import cached_property

from pprint import pprint
from dataclasses import dataclass

from tomlkit.toml_file import TOMLFile
import tomlkit


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


def get_mountpoint(partition_path):
    """Find mountpoint of given partition device. Returns empty string if not mounted."""
    args = f"lsblk {partition_path} --output mountpoint --noheadings".split()
    return run(args).strip()


def mount_if_needed(partition_path):
    """Mounts the given partition device if needed, and returns the mountpoint."""
    mountpoint = get_mountpoint(partition_path)
    if mountpoint:
        return mountpoint
    mount_stdout = run(
        f"udisksctl mount --block-device {partition_path} --options noatime".split()
    )
    print(f"udisksctl: {mount_stdout}")
    mountpoint = get_mountpoint(partition_path)
    if mountpoint:
        return mountpoint
    exit(f"{partition_path} somehow not mounted.")


class Cli:
    """Application logic and shared state."""

    def __init__(self, args):
        self.command = args.command
        self.vendor = args.vendor
        self.model = args.model
        self.serial = args.serial
        self.fuzzy = args.fuzzy
        self.preset_name = args.preset_name
        self.source_dirs = args.source_dir
        self.watch = args.watch
        self.save_preset = args.save_preset

        presets_path = Path("presets.toml")
        presets_path.touch(exist_ok=True)
        self.presets_file = TOMLFile(presets_path)

        if self.preset_name:
            self.load_preset()

        self.matching_devices = [
            d for d in all_devices() if self.device_matches_filter(d)
        ]

    def device_matches_filter(self, device):
        """Predicate for devices matching requested filter."""
        if self.fuzzy:
            return any(
                (
                    self.fuzzy in device.vendor,
                    self.fuzzy in device.model,
                    self.fuzzy in device.serial,
                )
            )
        return all(
            (
                self.vendor in device.vendor,
                self.model in device.model,
                self.serial in device.serial,
            )
        )

    @cached_property
    def device(self):
        """
        Returns the single device matching our filter. If there isn't strictly one device, we exit the process with an error.
        """
        match self.matching_devices:
            case [device]:
                return device
            case []:
                exit("No CircuitPython devices found.")
            case _:
                pprint(self.matching_devices)
                exit("Ambiguous choice of CircuitPython device.")

    @cached_property
    def mountpoint(self):
        """Mountpoint of current device."""
        return mount_if_needed(self.device.partition_path)

    def load_preset(self):
        presets = self.presets_file.read()
        preset = presets.get(self.preset_name, None)
        if preset is None:
            exit(
                f"Can't find preset '{self.preset_name}'. Valid choices: {list(presets.keys())}"
            )
        self.vendor = preset["vendor"]
        self.model = preset["model"]
        self.serial = preset["serial"]
        self.source_dirs = [Path(d) for d in preset["source_dirs"]]

    def walk_sources(self):
        """Generator that yields tuples of (top-level source directory, descendant path)."""
        for root in self.source_dirs:
            yield root, root
            for parent, subdirs, files in root.walk():
                for subdir in subdirs:
                    yield root, parent / subdir
                for file in files:
                    yield root, parent / file

    def upload(self):
        """Copy all source files onto the device."""
        for source_dir, source in self.walk_sources():
            if source.name[0] == "." or source.is_dir():
                continue
            rel_path = source.relative_to(source_dir)
            dest = self.mountpoint / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                # Round source timestamp to 2s resolution to match FAT drive. This prevents spurious timestamp mismatches.
                source_mtime = (source.stat().st_mtime // 2) * 2
                dest_mtime = dest.stat().st_mtime
                if source_mtime == dest_mtime:
                    continue
            print(f"Copying {source_dir / rel_path}")
            shutil.copy2(source, dest)
        print("Upload complete")

    def run(self):
        """Main entry point."""
        commands = {
            "list": self.list_command,
            "connect": self.connect_command,
            "upload": self.upload_command,
            "preset_upload": self.preset_upload_command,
        }
        commands[self.command]()

    def upload_watch(self):
        """Implements --watch flag for continuously uploading code."""
        from inotify_simple import INotify, flags

        watcher = INotify()

        # Maps inotify descriptors to source directories.
        descriptor_to_path = {}
        for _, source_dir in self.walk_sources():
            if not source_dir.is_dir():
                continue
            print(f"Watching source directory {source_dir} for changes.")
            descriptor = watcher.add_watch(
                source_dir,
                flags.CREATE
                | flags.MODIFY
                | flags.ATTRIB
                | flags.DELETE
                | flags.DELETE_SELF,
            )
            descriptor_to_path[descriptor] = source_dir

        while True:
            need_upload = False
            # Use a small read_delay to coalesce short bursts of events (e.g.
            # copying multiple files from another location).
            for event in watcher.read(read_delay=100):
                source_dir = descriptor_to_path[event.wd]
                path = source_dir / event.name
                print(f"{path} modified.")
                need_upload = True
            if need_upload:
                self.upload()

    def list_command(self):
        """list subcommand."""
        print("Matching devices:")
        pprint(self.matching_devices)

    def connect_command(self):
        """connect subcommand."""
        print("Launching minicom for ")
        pprint(device)
        execlp("minicom", "minicom", "-D", device.serial_path)

    def upload_command(self):
        """upload subcommand."""
        print("Uploading to device: ")
        pprint(self.device)
        if self.save_preset:
            name = self.save_preset
            presets = self.presets_file.read()
            preset = presets.get(name, tomlkit.table())

            preset["vendor"] = self.device.vendor
            preset["model"] = self.device.model
            preset["serial"] = self.device.serial
            preset["source_dirs"] = [str(d.resolve()) for d in self.source_dirs]
            preset["source_dirs"].multiline(True)

            presets[name] = preset
            self.presets_file.write(presets)
        self.upload()

        if self.watch:
            self.upload_watch()

    def preset_upload_command(self):
        self.upload_command()
