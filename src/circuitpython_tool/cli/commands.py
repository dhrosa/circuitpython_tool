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
from shutil import rmtree, which
from sys import argv, exit, stderr, stdout

import rich_click as click
from rich import get_console, print, traceback
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Confirm
from rich.rule import Rule
from rich_click import argument, option

from .. import VERSION, fs
from ..async_iter import time_batched
from ..hw import Device, Query, devices_to_toml
from . import Group, devices_table, uf2_commands
from .decorators import pass_shared_state
from .params import DeviceParam, FakeDeviceParam, QueryParam
from .shared_state import SharedState

logger = logging.getLogger(__name__)

PROGRAM_NAME = "circuitpython-tool"
"""Program name in help messages."""

COMPLETE_VAR = "_CIRCUITPYTHON_TOOL_COMPLETE"
"""Environment variable for shell completion support."""


def set_log_level(context: click.Context, param: click.Parameter, level: str) -> None:
    """Eager callback for --log-level flag."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=Console(stderr=True),
                markup=True,
                omit_repeated_times=False,
            ),
        ],
    )


@click.version_option(VERSION, "--version", "-v", prog_name=PROGRAM_NAME)
@click.group(
    cls=Group,
    context_settings=dict(
        help_option_names=["-h", "--help"],
    ),
    epilog=f"Version: {VERSION}",
)
@option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    callback=set_log_level,
    is_eager=True,
    expose_value=False,
    envvar="LOG_LEVEL",
    help="Only display logs at or above ths level.",
)
@option(
    "--fake-device-config",
    "-f",
    type=FakeDeviceParam(),
    expose_value=False,
    envvar="FAKE_DEVICE_CONFIG",
    # Force evaluation of this paramter early so that later parameters can
    # assume the config has already been found.
    is_eager=True,
    help="Path to TOML configuration file for fake devices. For use in tests and demos.",
)
def main() -> None:
    """Tool for interfacing with CircuitPython devices."""

    # Setup pretty traceback handler in a way that's relatively compact and
    # quiet, so that exceptions generally fit within a fraction of the terminal
    # window.

    # Import modules without aliased names.
    import click
    import rich_click

    traceback.install(
        show_locals=True,
        # Suppress frames from uninteresting wrapper functions, and the top-level wrapper script.
        suppress=[click, rich_click, argv[0]],
        max_frames=3,
        extra_lines=1,
    )


@main.command
def completion() -> None:
    """
    Output shell commands needed for auto-completion.

    Evaluating the output of this command will allow auto-completion of this
    program\'s arguments. This can be done as a one-off using::

      eval "$(circuitpython-tool completion)"

    or by putting the following line in your shell config file (e.g. ``~/.bashrc``)::

      source "$(circuitpython-tool completion)"
    """
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


@main.command(linux_only=True)
@argument("query", type=QueryParam(), default=Query.any())
@option(
    "--save",
    "-s",
    "fake_device_save_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="If set, save devices to a TOML file for later recall using the ``--fake-devices`` flag.",
)
@pass_shared_state
def devices(
    state: SharedState, query: Query, fake_device_save_path: Path | None
) -> None:
    """
    List all connected CircuitPython devices.

    If ``QUERY`` is specified, only devices matching that query are listed."""
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


@main.command(linux_only=True)
@argument("device", type=DeviceParam(), required=True)
@option(
    "--dir",
    "-d",
    "source_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=False,
    help="Path containing source code to upload. "
    "If not specified, the source directory is guessed by searching the current directory and "
    "its descendants for user code (e.g. ``code.py``).",
)
@option(
    "--circup/--no-circup",
    default=True,
    help="If ``True``, use ``circup`` to automatically install "
    "library dependencies on the target device.",
)
@option(
    "--mode",
    default="watch",
    type=click.Choice(choices=["single-shot", "watch"]),
    help="Whether to upload code once, or continuously.",
)
@option(
    "--batch-period",
    type=float,
    default=0.25,
    help="Batch filesystem events that happen within this period. "
    "This reduces spurious uploads when files update in quick succession. "
    "Unit: seconds",
)
def upload(
    device: Device,
    source_dir: Path | None,
    circup: bool,
    mode: str,
    batch_period: float,
) -> None:
    """
    Continuously upload code to device in response to source file changes.

    The contents of the specified source directory will be copied onto the given
    CircuitPython device.

    If ``--mode`` is ``single-shot``, then the code is uploaded and then the command exits.

    If ``--mode`` is ``watch``, then this commnd will perform one upload, and then
    will continue running. The command will wait for filesystem events from all
    paths and descendant paths of the source tree, and will re-upload code to
    the device on each event.
    """
    source_dir = get_source_dir(source_dir)
    if not fs.contains_main_code_file(source_dir) and not Confirm.ask(
        f"{source_dir} does not appear to contain any CircuitPython code."
        "Do you want to continue?"
    ):
        exit(1)
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

    if mode == "single-shot":
        print("👍 Upload [green]complete[/].")
        exit()

    events = time_batched(
        fs.watch_all(source_dirs), delay=lambda: asyncio.sleep(batch_period)
    )

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


@main.command(linux_only=True)
@argument("device", type=DeviceParam(), required=True)
def clean(device: Device) -> None:
    """Deletes all files on the target device, and creates an empty boot.py and code.py on it."""
    print(device)
    if not Confirm.ask(
        "This will delete all files on your device.\nDo you want to continue?"
    ):
        print("[yellow]Cancelling[/]")
        exit(1)
    mountpoint = device.mount_if_needed()
    with get_console().status("Deleting files."):
        for path in mountpoint.iterdir():
            if path == mountpoint / "boot_out.txt":
                logging.info(f"Skipping deletion of {path}")
                continue
            if path.is_dir():
                logging.info(f"Deleting directory {path}")
                rmtree(path)
            else:
                logging.info(f"Deleting file {path}")
                path.unlink()
    print(f"All files in {mountpoint} deleted.")
    for name in ("boot.py", "code.py"):
        path = mountpoint / name
        logging.info(f"Creating {path}")
        path.touch()
    print("👍 Cleanup [green]complete[/].")


@main.command(linux_only=True)
@argument("device", type=DeviceParam(), required=True)
def connect(device: Device) -> None:
    """Connect to a device's serial terminal."""
    logger.info("Launching minicom for ")
    logger.info(device)
    assert device.serial_path is not None
    execlp("minicom", "minicom", "-D", str(device.serial_path))


@main.command(linux_only=True)
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


@main.command(linux_only=True)
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


main.add_command(uf2_commands.uf2)


def circup_sync(mountpoint: Path) -> None:
    """Use 'circup' to install library dependencies onto device."""
    if not (circup := which("circup")):
        print(
            "🤷 [i]circup[/] command [red]not found[/]. "
            "Install it using e.g.: `pip install circup`"
        )
        return
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
