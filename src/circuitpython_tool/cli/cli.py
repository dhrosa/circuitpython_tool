"""User-facing command-line interface using `click`.

This is effectively the top-level code when the tool is executed as a program.

Any code directly interfacing with `rich` is housed here to avoid standalone
parts of the code being tied up with console output.

"""

import asyncio
import logging
from collections.abc import Callable, Iterable
from functools import wraps
from os import execlp
from pathlib import Path
from sys import exit
from typing import Concatenate, ParamSpec, TypeVar
from urllib.request import urlopen

import rich_click as click
from rich import get_console, print, progress, traceback
from rich.logging import RichHandler
from rich.table import Table

from .. import VERSION, fs
from ..async_iter import time_batched
from ..hw import fake_device, partition
from ..hw.device import Device
from ..hw.query import Query
from ..hw.uf2_device import Uf2Device
from ..uf2 import Board
from . import completion
from .config import Config, ConfigStorage, DeviceLabel
from .params import (
    BoardParam,
    ConfigStorageParam,
    FakeDeviceParam,
    LocaleParam,
    label_or_query_argument,
)
from .shared_state import SharedState

# Use `rich` for tracebacks and logging.
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


def _render_device(self: Device) -> Table:
    table = Table("Property", "Value")
    table.add_row("Vendor", self.vendor)
    table.add_row("Model", self.model)
    table.add_row("Serial", self.serial)
    table.add_row("Partition Path", str(self.partition_path))
    table.add_row("Serial Path", str(self.serial_path))
    table.add_row("Mountpoint", str(self.get_mountpoint()))
    return table


setattr(Device, "__rich__", _render_device)


def get_query(device_labels: dict[str, DeviceLabel], arg: str) -> Query:
    """Extract query from a string specifying either a device label or a query.

    Raises ValueError if the string matched neither."""
    for k, v in device_labels.items():
        if arg == k:
            return v.query
    return Query.parse(arg)


pass_shared_state = click.make_pass_decorator(SharedState, ensure=True)
"""Decorator for passing SharedState to a function."""

# These can be removed in python 3.12
#
# Type variables for return value and function parameters.
R = TypeVar("R")
P = ParamSpec("P")


def pass_config_storage(
    f: Callable[Concatenate[ConfigStorage, P], R]
) -> Callable[P, R]:
    """Decorator for passing ConfigStorage to a function."""

    @pass_shared_state
    @wraps(f)
    def inner(state: SharedState, /, *args: P.args, **kwargs: P.kwargs) -> R:
        return f(state.config_storage, *args, **kwargs)

    return inner


def pass_read_only_config(f: Callable[Concatenate[Config, P], R]) -> Callable[P, R]:
    """Decorator for supplying a function with a read-only snapshot of our current Config."""

    @pass_config_storage
    @wraps(f)
    def inner(config_storage: ConfigStorage, /, *args: P.args, **kwargs: P.kwargs) -> R:
        with config_storage.open() as config:
            return f(config, *args, **kwargs)

    return inner


@click.version_option(VERSION, "--version", "-v")
@click.group(
    context_settings=dict(
        help_option_names=["-h", "--help"], auto_envvar_prefix="CIRCUITPYTHON_TOOL"
    ),
    epilog=f"Version: {VERSION}",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=ConfigStorageParam(),
    default=ConfigStorage(),
    expose_value=False,
    show_envvar=True,
    # Force evaluation of this paramter early so that later parameters can
    # assume the config has already been found.
    is_eager=True,
    help="Path to configuration TOML file for device labels and source trees.",
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    show_envvar=True,
    help="Only display logs at or above ths level.",
)
@click.option(
    "--fake-device-config",
    "-f",
    type=FakeDeviceParam(),
    expose_value=False,
    show_envvar=True,
    # Force evaluation of this paramter early so that later parameters can
    # assume the config has already been found.
    is_eager=True,
    help="Path to TOML configuration file for fake devices. For use in tests and demos.",
)
def main(log_level: str) -> None:
    """Tool for interfacing with CircuitPython devices."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)


@main.command()
@label_or_query_argument("query", default=Query.any())
@click.option(
    "-s",
    "--save",
    "fake_device_save_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="If set, save devices to a TOML file for later recall using the --fake-devices flag.",
)
@pass_read_only_config
@pass_shared_state
def devices(
    state: SharedState, config: Config, query: Query, fake_device_save_path: Path | None
) -> None:
    """List all connected CircuitPython devices.

    If QUERY is specified, only devices matching that query are listed."""
    devices = query.matching_devices(state.all_devices())
    if devices:
        print("Connected CircuitPython devices:", devices_table(devices))
    else:
        print(":person_shrugging: [blue]No[/] connected CircuitPython devices found.")

    if fake_device_save_path:
        logging.info(f"Saving device list to {str(fake_device_save_path)}")
        fake_device_save_path.write_text(fake_device.to_toml(devices))


@main.group()
def label() -> None:
    """Manage device labels."""
    pass


@label.command("list")
@pass_read_only_config
def label_list(config: Config) -> None:
    """List all device labels."""
    labels = config.device_labels
    if not labels:
        print(":person_shrugging: [blue]No[/] existing labels found.")
        return
    table = Table("Label", "Query")
    for name, label in config.device_labels.items():
        table.add_row(name, label.query.as_str())
    print(table)


@label.command("add")
@click.argument("key", required=True, shell_complete=completion.device_label)
@label_or_query_argument("query")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Add the new label even if a label with the same name already exists."
    "The new QUERY value will override the previous stored value.",
)
@pass_config_storage
def label_add(
    config_storage: ConfigStorage, key: str, query: Query, force: bool
) -> None:
    """Add a new device label.

    Creates a new device label with the name KEY, referencing the given QUERY.
    """
    with config_storage.open() as config:
        labels = config.device_labels
        old_label = labels.get(key)
        if old_label:
            if force:
                logger.info(f"Label [blue]{key}[/] already exists. Proceeding anyway.")
            else:
                print(
                    f":thumbs_down: Label [red]{key}[/] already exists: ",
                    old_label.query.as_str(),
                )
                exit(1)

        label = DeviceLabel(query)
        labels[key] = label
    print(
        f":thumbs_up: Label [blue]{key}[/] added [green]successfully[/]: {label.query.as_str()}"
    )


@label.command("remove")
@click.confirmation_option(
    "--yes", "-y", prompt="Are you sure you want to delete this label?"
)
@click.argument("label_name", shell_complete=completion.device_label)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Return success even if there was no matching label to remove.",
)
@pass_config_storage
def label_remove(config_storage: ConfigStorage, label_name: str, force: bool) -> None:
    """Delete a device label."""
    with config_storage.open() as config:
        label = config.device_labels.get(label_name)
        if label:
            logger.debug(f"Found label [blue]{label_name}[/]: {label}")
            del config.device_labels[label_name]
        elif force:
            logger.info(f"Label [blue]{label_name}[/] not found. Proceeding anyway.")
        else:
            print(f":thumbs_down: Label [red]{label_name}[/] does not exist.")
            exit(1)
    print(f":thumbs_up: Label [blue]{label_name}[/] [green]successfully[/] deleted.")


def get_source_dir(source_dir: Path | None) -> Path:
    source_dir = source_dir or fs.guess_source_dir(Path.cwd())
    if source_dir is None:
        print(
            ":thumbs_down: [red]Failed[/red] to guess source directory. "
            "Either change the current directory, "
            "or explicitly specify the directory using [blue]--dir[/]."
        )
        exit(1)
    return source_dir


@main.command
@click.option(
    "--dir",
    "-d",
    "source_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=False,
    help="Path containing source code to upload. "
    "If not specified, the source directory is guessed by searching the current directory and "
    "its descendants for user code (e.g. code.py).",
)
@label_or_query_argument("query", required=True)
def upload(source_dir: Path | None, query: Query) -> None:
    """Upload code to device."""
    source_dir = get_source_dir(source_dir)
    print(f"Source directory: {source_dir}")
    device = distinct_device(query)
    mountpoint = device.mount_if_needed()
    print("Uploading to device: ", device)
    fs.upload([source_dir], mountpoint)
    print(":thumbs_up: Upload [green]succeeded.")


@main.command
@click.option(
    "--dir",
    "-d",
    "source_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=False,
    help="Path containing source code to upload. "
    "If not specified, the source directory is guessed by searching the current directory and "
    "its descendants for user code (e.g. code.py).",
)
@label_or_query_argument("query")
def watch(source_dir: Path | None, query: Query) -> None:
    """Continuously upload code to device in response to source file changes.

    The contents of the source tree TREE_NAME will be copied onto the device
    with the label LABEL_NAME.

    This command will always perform at least one upload. Then this command
    waits for filesystem events from all paths and descendant paths of the
    source tree. Currently this command will only properly track file
    modifications. Creation of new files and folders requires you to rerun this
    command in order to monitor them.
    """
    source_dir = get_source_dir(source_dir)
    print(f"Source directory: {source_dir}")
    device = distinct_device(query)
    print("Target device: ")
    print(device)
    # Always do at least one upload at the start.
    source_dirs = [source_dir]
    fs.upload(source_dirs, device.mount_if_needed())

    # TODO(dhrosa): Expose delay as a flag.
    events = time_batched(fs.watch_all(source_dirs), delay=lambda: asyncio.sleep(0.5))

    async def watch_loop() -> None:
        while True:
            with get_console().status(
                "[yellow]Waiting[/yellow] for file modification."
            ):
                modified_paths = await anext(events)
                logger.info(f"Modified paths: {[str(p) for p in modified_paths]}")
            with get_console().status("Uploading to device."):
                fs.upload(source_dirs, device.mount_if_needed())

    try:
        asyncio.run(watch_loop())
    except KeyboardInterrupt:
        print("Watch [magenta]cancelled[/magenta] by keyboard interrupt.")


@main.command
@label_or_query_argument("query")
def connect(query: Query) -> None:
    """Connect to a device's serial terminal."""
    device = distinct_device(query)
    logger.info("Launching minicom for ")
    logger.info(device)
    assert device.serial_path is not None
    execlp("minicom", "minicom", "-D", str(device.serial_path))


@main.group
def uf2() -> None:
    """Search and download CircuitPython UF2 binaries."""
    pass


@uf2.command
def versions() -> None:
    """List available CircuitPython boards."""
    table = Table()
    table.add_column("Id")
    table.add_column("Downloads", justify="right")
    table.add_column("Stable Version")
    table.add_column("Unstable Version")
    # Sort boards by decreasing popularity, then alphabetically.
    for board in sorted(Board.all(), key=lambda b: (-b.download_count, b.id)):
        table.add_row(
            board.id,
            str(board.download_count),
            board.stable_version.label if board.stable_version else "",
            board.unstable_version.label if board.unstable_version else "",
        )
    with get_console().pager():
        print(table)


@uf2.command
@click.argument("board", type=BoardParam(), required=True)
@click.option(
    "--locale",
    default="en_US",
    type=LocaleParam(),
    help="Locale for CircuitPython install.",
)
def url(board: Board, locale: str) -> None:
    """Print download URL for CircuitPython image."""
    print(board.download_url(board.most_recent_version, locale))


@uf2.command
@click.argument("board", type=BoardParam(), required=True)
@click.argument(
    "destination", type=click.Path(path_type=Path), required=False, default=Path.cwd()
)
@click.option(
    "--locale",
    default="en_US",
    type=LocaleParam(),
    help="Locale for CircuitPython install.",
)
def download(board: Board, locale: str, destination: Path) -> None:
    """Download CircuitPython image for the requested board.

    If DESTINATION is not provided, the file is downloaded to the current directory.
    If DESTINATION is a directory, the filename is automatically generated.
    """
    url = board.download_url(board.most_recent_version, locale)
    if destination.is_dir():
        destination /= url.split("/")[-1]
    print(f"Source: {url}")
    print(f"Destination: {destination}")
    response = urlopen(url)
    with progress.wrap_file(
        response,
        total=int(response.headers["Content-Length"]),
        description="Downloading",
    ) as f:
        destination.write_bytes(f.read())


@uf2.command
@label_or_query_argument("query")
def enter(query: Query) -> None:
    """Restart selected device into UF2 bootloader."""
    device = distinct_device(query)
    print(device)
    device.uf2_enter()
    # TODO(dhrosa): Wait for bootloader device to come online before exiting.


@uf2.command("devices")
def uf2_devices() -> None:
    """List connected devices that are in UF2 bootloader mode."""
    print(Uf2Device.all())


@uf2.command("mount")
def uf2_mount() -> None:
    """Mount connected UF2 bootloader device if needed and print the mountpoint."""
    device = distinct_uf2_device()
    print(device)
    mountpoint = partition.mountpoint(device.partition_path)
    if mountpoint:
        print(f"Device already mounted at {mountpoint}.")
        return
    mountpoint = partition.mount_if_needed(device.partition_path)
    print(f"Device mounted at {mountpoint}")


@uf2.command("unmount")
def uf2_unmount() -> None:
    """Unmount connected UF2 bootloader device if needed."""
    device = distinct_uf2_device()
    print(device)
    mountpoint = partition.mountpoint(device.partition_path)
    if not mountpoint:
        print("Device already not mounted.")
        return
    print(f"Device is currently mounted at {mountpoint}")
    partition.unmount_if_needed(device.partition_path)
    print("Device unmounted.")


@main.command
@label_or_query_argument("query")
def mount(query: Query) -> None:
    """Mounts the specified device if needed, and prints the mountpoint."""
    device = distinct_device(query)
    print(device)
    mountpoint = device.get_mountpoint()
    if mountpoint:
        print(f"Device already mounted at {mountpoint}.")
        return
    mountpoint = device.mount_if_needed()
    print(f"Device mounted at {mountpoint}")


@main.command
@label_or_query_argument("query")
def unmount(query: Query) -> None:
    """Unmounts the specified device if needed."""
    device = distinct_device(query)
    print(device)
    mountpoint = device.get_mountpoint()
    if not mountpoint:
        print("Device already not mounted.")
        return
    print(f"Device is currently mounted at {mountpoint}")
    device.unmount_if_needed()
    print("Device unmounted.")


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

    for device in sorted(devices, key=lambda d: d.key):
        table.add_row(
            device.vendor,
            device.model,
            device.serial,
            str(device.partition_path),
            str(device.serial_path),
            str(device.get_mountpoint()),
        )
    return table


def distinct_device(query: Query) -> Device:
    """Finds the distinct device matching the given query.

    If no devices match the query, or if more than one device matches the query,
    then we exit the process with an error.
    """
    state = click.get_current_context().ensure_object(SharedState)
    devices = state.all_devices()
    matching_devices = [d for d in devices if query.matches(d)]
    match matching_devices:
        case [device]:
            return device
        case []:
            print(":thumbs_down: [red]0[/red] matching devices found.")
            print(devices)
            exit(1)
        case _:
            count = len(matching_devices)
            print(
                ":thumbs_down: Ambiguous filter. ",
                f"[red]{count}[/red] matching devices found:",
                devices_table(matching_devices),
            )
            exit(1)


def distinct_uf2_device() -> Uf2Device:
    """Returns connected UF2 device.

    If there are no connected devices, or there are multiple devices, we exit
    the process with an error.

    """
    devices = Uf2Device.all()
    match count := len(devices):
        case 1:
            return next(iter(devices))
        case 0:
            print(":thumbs_down: [red]0[/red] UF2 bootloader devices found.")
            exit(1)
        case _:
            print(
                ":thumbs_down: Ambiguous device. "
                f"[red]{count}[/] UF2 bootloader devices found: ",
                devices,
            )
            exit(1)
