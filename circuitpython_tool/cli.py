import subprocess
from pathlib import Path
import shutil
from sys import exit
from os import execlp
from functools import cached_property

from .device import Device, all_devices
from .presets import Preset, PresetDatabase
from .fs import walk_all, watch_all

from rich.console import Console
from rich.table import Table
from rich import get_console, traceback, print

import logging
from rich.logging import RichHandler

traceback.install(show_locals=True)
logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(rich_tracebacks=True, markup=True, omit_repeated_times=False)
    ],
)
logger = logging.getLogger(__name__)

# Choosing to implement __rich__ render protocol via monkeypatching to decouple
# rendering logic from lower-level data structures.


def _render_preset(self):
    table = Table("Property", "Value")
    table.add_row("Vendor", self.vendor)
    table.add_row("Model", self.model)
    table.add_row("Serial", self.serial)
    table.add_row("Source Dirs", "\n".join(str(p) for p in self.source_dirs))
    return table


Preset.__rich__ = _render_preset


def _render_device(self):
    table = Table("Property", "Value")
    table.add_row("Vendor", self.vendor)
    table.add_row("Model", self.model)
    table.add_row("Serial", self.serial)
    table.add_row("Partition Path", str(self.partition_path))
    table.add_row("Serial Path", str(self.serial_path))
    table.add_row("Mountpoint", str(self.get_mountpoint()))
    return table


Device.__rich__ = _render_device


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
                print(":thumbs_down: [red]0[/red] matching devices found.")
                exit(1)
            case _:
                count = len(self.matching_devices)
                print(
                    f":thumbs_down: Ambiguous filter. [red]{count}[/red] matching devices found:",
                    self.devices_table(),
                )
                exit(1)

    def load_preset(self):
        try:
            preset = self.preset_db[self.preset_name]
        except KeyError:
            valid_choices = " | ".join(
                f"[blue]{name}[/]" for name in self.preset_db.keys()
            )
            print(
                f":thumbs_down: Cannot find preset [red]{self.preset_name}[/red]. Valid choices: {valid_choices}"
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
            case "watch":
                self.watch_command()
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
        print("Connected CircuitPython devices:", self.devices_table())

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
        print(f"Saving preset [blue]{self.new_preset_name}[/blue]: ", preset)
        self.preset_db[self.new_preset_name] = preset
        print(f":thumbs_up: [green]Successfully[/green] saved new preset.")

    def connect_command(self):
        """connect subcommand."""
        device = self.distinct_device()
        logger.info("Launching minicom for ")
        logger.info(device)
        execlp("minicom", "minicom", "-D", device.serial_path)

    def upload_command(self):
        """upload subcommand."""
        device = self.distinct_device()
        mountpoint = device.mount_if_needed()
        print("Uploading to device: ", device)
        self.upload(mountpoint)
        print(":thumbs_up: Upload [green]succeeded.")

    def watch_command(self):
        """watch subcommand."""
        device = self.distinct_device()
        mountpoint = device.mount_if_needed()
        print("Target device: ")
        print(device)
        # Always do at least one upload at the start.
        self.upload(mountpoint)

        events = iter(watch_all(self.source_dirs))
        try:
            while True:
                with self.console.status(
                    "[yellow]Waiting[/yellow] for file modification."
                ):
                    modified_paths = next(events)
                logger.info(f"Modified paths: {[str(p) for p in modified_paths]}")
                with self.console.status("Uploading to device."):
                    self.upload(mountpoint)
        except KeyboardInterrupt:
            print("Watch [magenta]cancelled[/magenta] by keyboard interrupt.")
            return
