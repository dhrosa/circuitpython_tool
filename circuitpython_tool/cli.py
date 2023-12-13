import logging
import shutil
from collections.abc import Iterable
from os import execlp
from pathlib import Path
from sys import exit

from rich import get_console, print, traceback
from rich.logging import RichHandler
from rich.table import Table

from .device import Device, all_devices
from .fs import walk_all, watch_all
from .presets import Preset, PresetDatabase

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


def devices_command():
    """devices subcommand."""
    devices = all_devices()
    if not devices:
        print(":person_shrugging: [blue]No[/] connected CircuitPython devices found.")
        return
    print("Connected CircuitPython devices:", devices_table(devices))


def preset_list_command(preset_db: PresetDatabase):
    """preset list command."""
    table = Table("Preset Name", "Vendor", "Model", "Serial", "Source Directories")
    for name, preset in preset_db.items():
        table.add_row(
            name,
            preset.vendor,
            preset.model,
            preset.serial,
            "\n".join(str(p) for p in preset.source_dirs),
        )
    print(table)


def preset_save_command(preset_db: PresetDatabase, preset_name: str, preset: Preset):
    """preset save command."""
    print(f"Saving preset [blue]{preset_name}[/blue]: ", preset)
    preset_db[preset_name] = preset
    print(":thumbs_up: [green]Successfully[/green] saved new preset.")


def upload_command(preset: Preset):
    """upload subcommand."""
    device = distinct_device(preset)
    mountpoint = device.mount_if_needed()
    print("Uploading to device: ", device)
    upload(preset.source_dirs, mountpoint)
    print(":thumbs_up: Upload [green]succeeded.")


def watch_command(preset: Preset):
    """watch subcommand."""
    device = distinct_device(preset)
    mountpoint = device.mount_if_needed()
    print("Target device: ")
    print(device)
    # Always do at least one upload at the start.
    source_dirs = preset.source_dirs
    upload(source_dirs, mountpoint)

    events = iter(watch_all(source_dirs))
    try:
        while True:
            with get_console().status(
                "[yellow]Waiting[/yellow] for file modification."
            ):
                modified_paths = next(events)
                logger.info(f"Modified paths: {[str(p) for p in modified_paths]}")
            with get_console().status("Uploading to device."):
                upload(source_dirs, mountpoint)
    except KeyboardInterrupt:
        print("Watch [magenta]cancelled[/magenta] by keyboard interrupt.")


def connect_command(preset: Preset):
    """connect subcommand"""
    device = distinct_device(preset)
    logger.info("Launching minicom for ")
    logger.info(device)
    execlp("minicom", "minicom", "-D", device.serial_path)


def devices_table(devices: Iterable[Device]) -> Table:
    """Render devices into a table."""
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

    for device in devices:
        table.add_row(
            device.vendor,
            device.model,
            device.serial,
            str(device.partition_path),
            str(device.serial_path),
            str(device.get_mountpoint()),
        )
    return table


def distinct_device(preset: Preset) -> Device:
    """Returns the single device matching our filter.

    If there isn't strictly one device, we exit the process with an error.
    """
    matching_devices = [d for d in all_devices() if preset.predicate(d)]
    match matching_devices:
        case [device]:
            return device
        case []:
            print(":thumbs_down: [red]0[/red] matching devices found.")
            exit(1)
        case _:
            count = len(matching_devices)
            print(
                ":thumbs_down: Ambiguous filter. ",
                f"[red]{count}[/red] matching devices found:",
                devices_table(matching_devices),
            )
            exit(1)


def upload(source_dirs: Iterable[Path], mountpoint: Path):
    """Copy all source files onto the device."""
    for source_dir, source in walk_all(source_dirs):
        if source.name[0] == "." or source.is_dir():
            continue
        rel_path = source.relative_to(source_dir)
        dest = mountpoint / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            # Round source timestamp to 2s resolution to match FAT drive.
            # This prevents spurious timestamp mismatches.
            source_mtime = (source.stat().st_mtime // 2) * 2
            dest_mtime = dest.stat().st_mtime
            if source_mtime == dest_mtime:
                continue
        logger.info(f"Copying {source_dir / rel_path}")
        shutil.copy2(source, dest)
    logger.info("Upload complete")


def run(args):
    command = args.command
    if command == "devices":
        devices_command()
        return

    # Commands below require access to preset database.
    preset_db = PresetDatabase()

    if command == "preset":
        match args.preset_command:
            case "list":
                preset_list_command(preset_db)
                return
            case "save":
                preset = Preset(
                    vendor=args.vendor,
                    model=args.model,
                    serial=args.serial,
                    source_dirs=args.source_dir,
                )
                device = distinct_device(preset)
                preset.vendor = device.vendor
                preset.model = device.model
                preset.serial = device.serial
                preset_save_command(preset_db, args.new_preset_name, preset)
                return
            case _:
                raise NotImplementedError(
                    f"Unknown 'preset' command: {args.preset_command}"
                )

    try:
        preset = preset_db[args.preset_name]
    except KeyError:
        valid_choices = " | ".join(f"[blue]{name}[/]" for name in preset_db.keys())
        print(f":thumbs_down: Cannot find preset [red]{args.preset_name}[/red].")
        print(f"Valid choices: {valid_choices}")
        exit(1)

    match command:
        case "upload":
            upload_command(preset)
        case "watch":
            watch_command(preset)
        case "connect":
            connect_command(preset)

    raise NotImplementedError(f"Unknown command: {command}")
