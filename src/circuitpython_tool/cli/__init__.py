"""Code common to modules in this package."""

# TODO(dhrosa): This file feels like a 'utils' library; figure out a better way to organize this.

import logging
from collections.abc import Iterable

import rich_click as click
from rich import print, traceback
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from ..hw import Device, Query, Uf2Device
from ..render import to_table
from .shared_state import SharedState

# Use `rich` for tracebacks and logging.
traceback.install(show_locals=True)

stderr_console = Console(stderr=True)

logging.basicConfig(
    # Default to WARNING for code that runs before main(). This level is overriden in main().
    level="WARNING",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            console=stderr_console,
            rich_tracebacks=True,
            markup=True,
            omit_repeated_times=False,
        )
    ],
)


def devices_table(devices: Iterable[Device]) -> Table:
    """Render devices into a table."""
    # Mypy incorrectly infers the type when this is inlined.
    sorted_devices = sorted(devices, key=lambda d: d.key)
    return to_table(Device, sorted_devices)


def uf2_devices_table(devices: Iterable[Uf2Device]) -> Table:
    """Render UF2 bootloader devices into a table."""
    return to_table(Uf2Device, devices)


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
