import subprocess
from pathlib import Path
import shutil
from sys import exit
from os import execlp
from functools import cached_property
from contextlib import suppress

from .device import Device, all_devices
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


def render_preset(preset):
    table = Table("Property", "Value")
    table.add_row("Vendor", preset.vendor)
    table.add_row("Model", preset.model)
    table.add_row("Serial", preset.serial)
    table.add_row("Source Dirs", "\n".join(str(p) for p in preset.source_dirs))
    return table


class Cli:
    """Application logic and shared state."""

    def __init__(self, args):
        self.console = get_console()

        self.command = args.command
        self.preset_command = args.preset_command
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

        self.matching_devices = [
            d for d in all_devices() if self.device_matches_filter(d)
        ]

    def device_matches_filter(self, device):
        """Predicate for devices matching requested filter."""
        return all(
            (
                self.vendor in device.vendor,
                self.model in device.model,
                self.serial in device.serial,
            )
        )

    def distinct_device(self):
        """
        Returns the single device matching our filter. If there isn't strictly one device, we exit the process with an error.
        """
        match self.matching_devices:
            case [device]:
                return device
            case []:
                logger.critical("No CircuitPython devices found.")
                exit(1)
            case _:
                print(self.devices_table())
                logger.critical("Ambiguous choice of CircuitPython device.")
                exit(1)

    def load_preset(self):
        try:
            preset = self.preset_db[self.preset_name]
        except KeyError:
            valid_choices = " | ".join(
                f"[green]{name}[/]" for name in self.preset_db.keys()
            )
            logger.critical(
                f"Can't find preset [blue]{self.preset_name}[/blue]. Valid choices: {valid_choices}",
                extra={"markup": True},
            )
            exit(1)
        self.vendor = preset.vendor
        self.model = preset.model
        self.serial = preset.serial
        self.source_dirs = preset.source_dirs

    def walk_sources(self):
        """Generator that yields tuples of (top-level source directory, descendant path)."""
        return walk_all(self.source_dirs)

    def upload(self, mountpoint):
        """Copy all source files onto the device."""
        for source_dir, source in self.walk_sources():
            if source.name[0] == "." or source.is_dir():
                continue
            rel_path = source.relative_to(source_dir)
            dest = mountpoint / rel_path
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

    def devices_table(self):
        """Rich table of connected devices matching filter."""
        table = Table()
        for column_name in (
            "Vendor",
            "Model",
            "Serial",
            "Partition Path",
            "Serial Path",
            "Mountpoint",
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
                str(device.get_mountpoint()),
            )
        return table

    def run(self):
        """Main entry point."""
        match self.command:
            case "devices":
                self.devices_command()
            case "connect" | "preset_connect":
                self.connect_command()
            case "upload":
                self.upload_command()
            case "preset":
                match self.preset_command:
                    case "list":
                        self.preset_list_command()
                    case "save":
                        self.preset_save_command()
                    case _:
                        raise NotImplementedError((self.command, self.preset_command))

            case "preset_list":
                self.preset_list_command()
            case "preset_save":
                self.preset_save_command()
            case _:
                raise NotImplementedError(self.command)

    def devices_command(self):
        """devices subcommand."""
        print(self.devices_table())

    def preset_list_command(self):
        """preset list command."""
        table = Table("Preset Name", "Vendor", "Model", "Serial", "Source Directories")
        for name, preset in self.preset_db.items():
            table.add_row(
                name,
                preset.vendor,
                preset.model,
                preset.serial,
                "\n".join(str(p) for p in preset.source_dirs),
            )
        print(table)

    def preset_save_command(self):
        """preset save command."""
        device = self.distinct_device()
        preset = Preset(
            vendor=device.vendor,
            model=device.model,
            serial=device.serial,
            source_dirs=self.source_dirs,
        )
        self.console.print(f"Saving new preset: [blue]{self.new_preset_name}")
        print(render_preset(preset))
        self.preset_db[self.new_preset_name] = preset

    def connect_command(self):
        """connect subcommand."""
        device = self.distinct_device()
        print("Launching minicom for ")
        print(device)
        execlp("minicom", "minicom", "-D", device.serial_path)

    def upload_command(self):
        """upload subcommand."""
        device = self.distinct_device()
        print("Uploading to device: ")
        print(device)
        mountpoint = device.mount_if_needed()
        self.upload(mountpoint)
        if not self.watch:
            return

        events = iter(watch_all(self.source_dirs))

        with suppress(KeyboardInterrupt):
            while True:
                with self.console.status("Waiting for file modification."):
                    modified_paths = next(events)
                logger.info(f"Modified paths: {[str(p) for p in modified_paths]}")
                with self.console.status("Uploading to device."):
                    self.upload(mountpoint)
