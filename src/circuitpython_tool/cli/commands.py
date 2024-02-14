"""User-facing command-line interface using `click`.

This is effectively the top-level code when the tool is executed as a program.

Any code directly interfacing with `rich` is housed here to avoid standalone
parts of the code being tied up with console output.

"""

import asyncio
import logging
from os import environ, execlp
from pathlib import Path
from sys import exit, stderr, stdout

import rich_click as click
from rich import get_console, print

from .. import VERSION, fs
from ..async_iter import time_batched
from ..hw import fake_device
from ..hw.query import Query
from . import (
    devices_table,
    distinct_device,
    label_commands,
    pass_read_only_config,
    pass_shared_state,
    uf2_commands,
)
from .config import Config, ConfigStorage
from .params import ConfigStorageParam, FakeDeviceParam, label_or_query_argument
from .shared_state import SharedState

logger = logging.getLogger(__name__)

COMPLETE_VAR = "_CIRCUITPYTHON_TOOL"
"""Environment variable for shell completion support."""


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


main.add_command(uf2_commands.uf2)
main.add_command(label_commands.label)


@main.command
def completion() -> None:
    """Output shell commands needed for auto-completion.

    Evaluating the output of this command will allow auto-completion of this
    program's arguments. This can be done as a one-off using:

    eval $(circuitpython-tool completion)

    or by putting the following line in your shell config file (e.g. ~/.bashrc):

    source $(circuitpython-tool completion)
    """

    # TODO(dhrosa): Document sourcing the pre-generated completion scripts.
    try:
        shell_path = Path(environ["SHELL"])
    except KeyError:
        print(":thumbs_down: $SHELL environment variable [red]not[/] set.")
        exit(1)

    tty_warning = """
    [yellow]WARNING[/]:
    If you're seeing this message in your terminal,
    then you probably meant to evaluate the output of this command in your shell.
    You can do this by as a one-off using:

    eval $(circuitpython-tool completion)

    or by putting the following line in your shell config file:

    source $(circuitpython-tool completion)
    """

    def maybe_emit_tty_warning() -> None:
        if stdout.isatty():
            print(tty_warning, file=stderr)

    environ[COMPLETE_VAR] = f"{shell_path.name}_source"
    # We print warning message at start and end of output so it's easier to
    # notice no matter how the output is scrolled.
    maybe_emit_tty_warning()
    try:
        main.main([], complete_var=COMPLETE_VAR)
    finally:
        maybe_emit_tty_warning()


@main.command()
@label_or_query_argument("query", default=Query.any())
@click.option(
    "--save",
    "-s",
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
@label_or_query_argument("query", required=True)
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
@label_or_query_argument("query", required=True)
def connect(query: Query) -> None:
    """Connect to a device's serial terminal."""
    device = distinct_device(query)
    logger.info("Launching minicom for ")
    logger.info(device)
    assert device.serial_path is not None
    execlp("minicom", "minicom", "-D", str(device.serial_path))


@main.command
@label_or_query_argument("query", required=True)
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
@label_or_query_argument("query", required=True)
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
