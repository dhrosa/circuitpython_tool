"""Code common to modules in this package."""

# TODO(dhrosa): This file feels like a 'utils' library; figure out a better way to organize this.

import logging
from collections.abc import Callable, Iterable
from datetime import datetime
from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar

import rich_click as click
from humanize import naturaltime
from rich import print, traceback
from rich.logging import RichHandler
from rich.table import Table

from ..hw.device import Device
from ..hw.query import Query
from ..hw.uf2_device import Uf2Device
from .config import Config, ConfigStorage
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


def render_device(self: Device) -> Table:
    table = Table("Property", "Value")
    table.add_row("Vendor", self.vendor)
    table.add_row("Model", self.model)
    table.add_row("Serial", self.serial)
    table.add_row("Partition Path", str(self.partition_path))
    table.add_row("Serial Path", str(self.serial_path))
    table.add_row("Mountpoint", str(self.get_mountpoint()))
    table.add_row("Connection Time", pretty_datetime(self.connection_time))
    return table


# TODO(dhrosa): There has got to be a better way to automatically pretty-print
# without leaking Rich details into other modules.
setattr(Device, "__rich__", render_device)


def render_uf2_device(self: Uf2Device) -> Table:
    table = Table("Property", "Value")
    table.add_row("Vendor", self.vendor)
    table.add_row("Model", self.model)
    table.add_row("Serial", self.serial)
    table.add_row("Partition Path", str(self.partition_path))
    table.add_row("Mountpoint", str(self.get_mountpoint()))
    table.add_row("Connection Time", pretty_datetime(self.connection_time))
    return table


setattr(Uf2Device, "__rich__", render_uf2_device)


def pretty_datetime(timestamp: datetime) -> str:
    """Human-readable rendering of a timestamp and its delta from now."""
    delta = naturaltime(datetime.now() - timestamp)
    return f"{timestamp:%x %X} ({delta})"


def devices_table(devices: Iterable[Device]) -> Table:
    """Render devices into a table."""
    table = Table(
        "Vendor",
        "Model",
        "Serial",
        "Partition Path",
        "Serial Path",
        "Mountpoint",
        "Connection Time",
    )

    for column in table.columns:
        column.overflow = "fold"

    for device in sorted(devices, key=lambda d: d.key):
        table.add_row(
            device.vendor,
            device.model,
            device.serial,
            str(device.partition_path),
            str(device.serial_path),
            str(device.get_mountpoint()),
            pretty_datetime(device.connection_time),
        )
    return table


def uf2_devices_table(devices: Iterable[Uf2Device]) -> Table:
    """Render UF2 bootloader devices into a table."""
    table = Table(
        "Vendor", "Model", "Serial", "Partition Path", "Mountpoint", "Connection Time"
    )
    for column in table.columns:
        column.overflow = "fold"
    for device in devices:
        table.add_row(
            device.vendor,
            device.model,
            device.serial,
            str(device.partition_path),
            str(device.get_mountpoint()),
            pretty_datetime(device.connection_time),
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
                uf2_devices_table(devices),
            )
            exit(1)


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
