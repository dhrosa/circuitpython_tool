"""User-facing command-line interface using `click`.

This is effectively the top-level code when the tool is executed as a program.

Any code directly interfacing with `rich` is housed here to avoid standalone
parts of the code being tied up with console output.

"""

import asyncio
import logging
import shlex
import subprocess
from os import environ, execlp
from pathlib import Path
from shutil import which
from sys import exit, stderr, stdout

import rich_click as click
from rich import get_console, print
from rich.rule import Rule
from rich_click import argument, option

from .. import VERSION, fs
from ..async_iter import time_batched
from ..hw import Device, Query, devices_to_toml
from . import devices_table, pass_shared_state, uf2_commands
from .params import DeviceParam, FakeDeviceParam, QueryParam
from .shared_state import SharedState

logger = logging.getLogger(__name__)

PROGRAM_NAME = "circuitpython-tool"
"""Program name in help messages."""

COMPLETE_VAR = "_CIRCUITPYTHON_TOOL_COMPLETE"
"""Environment variable for shell completion support."""


@click.version_option(VERSION, "--version", "-v", prog_name=PROGRAM_NAME)
@click.group(
    context_settings=dict(
        help_option_names=["-h", "--help"],
        auto_envvar_prefix="CIRCUITPYTHON_TOOL",
    ),
    epilog=f"Version: {VERSION}",
)
@option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    show_envvar=True,
    help="Only display logs at or above ths level.",
)
@option(
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


@main.command
def completion() -> None:
    """Output shell commands needed for auto-completion.

    Evaluating the output of this command will allow auto-completion of this
    program's arguments. This can be done as a one-off using:

    eval "$(circuitpython-tool completion)"

    or by putting the following line in your shell config file (e.g. ~/.bashrc):

    source "$(circuitpython-tool completion)"
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

    eval "$(circuitpython-tool completion)"

    or by putting the following line in your shell config file:

    source "$(circuitpython-tool completion)"

    or to avoid execution time of Python code, you can redirect the output of
    this command to a file and `source` that file in your shell config file.
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
@argument("query", type=QueryParam(), default=Query.any())
@option(
    "--save",
    "-s",
    "fake_device_save_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="If set, save devices to a TOML file for later recall using the --fake-devices flag.",
)
@pass_shared_state
def devices(
    state: SharedState, query: Query, fake_device_save_path: Path | None
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
        fake_device_save_path.write_text(devices_to_toml(devices))


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
@argument("device", type=DeviceParam(), required=True)
@option(
    "--dir",
    "-d",
    "source_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=False,
    help="Path containing source code to upload. "
    "If not specified, the source directory is guessed by searching the current directory and "
    "its descendants for user code (e.g. code.py).",
)
@option(
    "--circup/--no-circup",
    default=False,
    help="If true, use `circup` to automatically install "
    "library dependencies on the target device.",
)
def upload(device: Device, source_dir: Path | None, circup: bool) -> None:
    """Upload code to device."""
    source_dir = get_source_dir(source_dir)
    print(f"Source directory: {source_dir}")
    mountpoint = device.mount_if_needed()
    print("Uploading to device: ", device)
    fs.upload([source_dir], mountpoint)
    print(":thumbs_up: Upload [green]succeeded.")
    if circup:
        circup_sync(mountpoint)


@main.command
@argument("device", type=DeviceParam(), required=True)
@option(
    "--dir",
    "-d",
    "source_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=False,
    help="Path containing source code to upload. "
    "If not specified, the source directory is guessed by searching the current directory and "
    "its descendants for user code (e.g. code.py).",
)
@option(
    "--circup/--no-circup",
    default=False,
    help="If true, use `circup` to automatically install "
    "library dependencies on the target device.",
)
def watch(device: Device, source_dir: Path | None, circup: bool) -> None:
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
    source_dirs = [source_dir]
    print(f"Source directory: {source_dir}")
    print("Target device: ")
    print(device)

    def sync() -> None:
        mountpoint = device.mount_if_needed()
        with get_console().status("Uploading to device."):
            fs.upload(source_dirs, mountpoint)
        if circup:
            circup_sync(mountpoint)

    # Always do at least one upload at the start.
    sync()

    # TODO(dhrosa): Expose delay as a flag.
    events = time_batched(fs.watch_all(source_dirs), delay=lambda: asyncio.sleep(0.5))

    async def watch_loop() -> None:
        while True:
            with get_console().status(
                "[yellow]Waiting[/yellow] for file modification."
            ):
                modified_paths = await anext(events)
                logger.info(f"Modified paths: {[str(p) for p in modified_paths]}")
            sync()

    try:
        asyncio.run(watch_loop())
    except KeyboardInterrupt:
        print("Watch [magenta]cancelled[/magenta] by keyboard interrupt.")


@main.command
@argument("device", type=DeviceParam(), required=True)
def connect(device: Device) -> None:
    """Connect to a device's serial terminal."""
    logger.info("Launching minicom for ")
    logger.info(device)
    assert device.serial_path is not None
    execlp("minicom", "minicom", "-D", str(device.serial_path))


@main.command
@argument("device", type=DeviceParam(), required=True)
def mount(device: Device) -> None:
    """Mounts the specified device if needed, and prints the mountpoint."""
    print(device)
    mountpoint = device.get_mountpoint()
    if mountpoint:
        print(f"Device already mounted at {mountpoint}.")
        return
    mountpoint = device.mount_if_needed()
    print(f"Device mounted at {mountpoint}")


@main.command
@argument("device", type=DeviceParam(), required=True)
def unmount(device: Device) -> None:
    """Unmounts the specified device if needed."""
    print(device)
    mountpoint = device.get_mountpoint()
    if not mountpoint:
        print("Device already not mounted.")
        return
    print(f"Device is currently mounted at {mountpoint}")
    device.unmount_if_needed()
    print("Device unmounted.")


def circup_sync(mountpoint: Path) -> None:
    """Use 'circup' to install library dependencies onto device."""
    if not (circup := which("circup")):
        print(
            "🤷 [i]circup[/] command [red]not found[/]. "
            "Install it using e.g.: `pip install circup`"
        )
        exit(1)
    args = [
        circup,
        "--path",
        str(mountpoint),
        "install",
        "--auto",
    ]
    print("Running command: ", shlex.join(args))
    print(Rule("begin circup output"))
    with subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ) as process:
        assert process.stdout
        while out := process.stdout.read(1):
            stdout.write(out.decode())
    print(Rule("end circup output"))
    print("👍 Circup sync [green]complete[/].")
