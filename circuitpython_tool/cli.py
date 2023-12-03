import subprocess
from pathlib import Path
import shutil
from sys import exit
from os import execlp
from functools import cached_property

from pprint import pprint

from .device import Device, all_devices
from .presets import Preset, PresetDatabase
from .fs import walk_all, watch_all


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
        self.new_preset_name = args.new_preset_name

        self.preset_db = PresetDatabase()
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
            print(f"Copying {source_dir / rel_path}")
            shutil.copy2(source, dest)
        print("Upload complete")

    def run(self):
        """Main entry point."""
        commands = {
            "list": self.list_command,
            "connect": self.connect_command,
            "preset_connect": self.connect_command,
            "upload": self.upload_command,
            "preset_upload": self.upload_command,
        }
        commands[self.command]()

    def list_command(self):
        """list subcommand."""
        print("Matching devices:")
        pprint(self.matching_devices)

    def connect_command(self):
        """connect subcommand."""
        print("Launching minicom for ")
        pprint(self.device)
        execlp("minicom", "minicom", "-D", self.device.serial_path)

    def upload_command(self):
        """upload subcommand."""
        print("Uploading to device: ")
        pprint(self.device)
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

        for modified_paths in watch_all(self.source_dirs):
            print(f"Modified paths: {[str(p) for p in modified_paths]}")
            self.upload()
