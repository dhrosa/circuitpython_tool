import subprocess
from pathlib import Path
import shutil
from sys import exit
from os import execlp
from functools import cached_property
from contextlib import suppress

from .device import Device, all_devices, fake_devices
from .presets import Preset, PresetDatabase
from .fs import walk_all, watch_all

from rich.console import Console
from rich.table import Table
from rich import get_console
from rich import traceback
from rich import print

import logging
from rich.logging import RichHandler

traceback.install(show_locals=True)
logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)


class Cli:
    """Application logic and shared state."""

    def __init__(self, args):
        self.console = get_console()

        self.command = args.command
        self.vendor = args.vendor
        self.model = args.model
        self.serial = args.serial
        self.preset_name = args.preset_name
        self.source_dirs = args.source_dir
        self.watch = args.watch
        self.new_preset_name = args.new_preset_name

        self.preset_db = PresetDatabase()
        if self.preset_name:
            self.load_preset()

        if args.fake_device_count:
            devices = fake_devices(args.fake_device_count)
        else:
            devices = all_devices()

        self.matching_devices = [d for d in devices if self.device_matches_filter(d)]

    def device_matches_filter(self, device):
        """Predicate for devices matching requested filter."""
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
                print(self.matching_devices)
                exit("Ambiguous choice of CircuitPython device.")

    @cached_property
    def mountpoint(self):
        """Mountpoint of current device."""
        return self.device.mount_if_needed()

    def load_preset(self):
        try:
            preset = self.preset_db[self.preset_name]
        except KeyError:
            exit(
                f"Can't find preset '{self.preset_name}'. Valid choices: {list(self.preset_db.keys())}"
            )
        self.vendor = preset.vendor
        self.model = preset.model
        self.serial = preset.serial
        self.source_dirs = preset.source_dirs

    def walk_sources(self):
        """Generator that yields tuples of (top-level source directory, descendant path)."""
        return walk_all(self.source_dirs)

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
            logger.info(f"Copying {source_dir / rel_path}")
            shutil.copy2(source, dest)
        logger.info("Upload complete")

    def run(self):
        """Main entry point."""
        match self.command:
            case "list":
                self.list_command()
            case "connect" | "preset_connect":
                self.connect_command()
            case "upload" | "preset_upload":
                self.upload_command()
            case "preset_list":
                self.preset_list_command()
            case _:
                raise NotImplementedError(self.command)

    def list_command(self):
        """list subcommand."""
        table = Table(title="CircuitPython Devices")
        for column_name in (
            "Vendor",
            "Model",
            "Serial",
            "Partition Path",
            "Serial Path",
        ):
            # Make sure full paths are rendered even if terminal is too small.
            table.add_column(column_name, overflow="fold")

        for device in self.matching_devices:
            table.add_row(
                device.vendor,
                device.model,
                device.serial,
                str(device.partition_path),
                str(device.serial_path),
            )

        console = Console()
        console.print(table, overflow="fold")

    def preset_list_command(self):
        """preset list command."""
        table = Table("Name", "Vendor", "Model", "Serial", "Source Directories")
        table.title = "Presets"
        for name, preset in self.preset_db.items():
            table.add_row(
                name, preset.vendor, preset.model, preset.model, preset.serial, ""
            )
        self.console.print(table)

    def connect_command(self):
        """connect subcommand."""
        print("Launching minicom for ")
        print(self.device)
        execlp("minicom", "minicom", "-D", self.device.serial_path)

    def upload_command(self):
        """upload subcommand."""
        print("Uploading to device: ")
        print(self.device)
        if self.new_preset_name:
            self.preset_db[self.new_preset_name] = Preset(
                vendor=self.device.vendor,
                model=self.device.model,
                serial=self.device.serial,
                source_dirs=self.source_dirs,
            )
        self.upload()
        if not self.watch:
            return

        events = iter(watch_all(self.source_dirs))

        with suppress(KeyboardInterrupt):
            while True:
                with self.console.status("Waiting for file modification."):
                    modified_paths = next(events)
                logger.info(f"Modified paths: {[str(p) for p in modified_paths]}")
                with self.console.status("Uploading to device."):
                    self.upload()
