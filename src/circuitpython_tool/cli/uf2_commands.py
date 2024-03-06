"""'uf2' subcommands."""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from logging import getLogger
from pathlib import Path
from shutil import rmtree
from sys import stdout
from tempfile import mkdtemp
from urllib.request import urlopen

import rich_click as click
from humanize import naturaldelta
from readchar import key, readkey
from rich import get_console, print, progress
from rich.console import Group as RichGroup
from rich.live import Live
from rich.pretty import Pretty
from rich.prompt import Confirm
from rich.table import Table
from rich_click import argument, option

from .. import static
from ..hw import Device, Query, Uf2Device
from ..request_cache import RequestCache
from ..uf2 import Block, Board
from . import Command, Group, distinct_device, distinct_uf2_device, uf2_devices_table
from .params import BoardParam, DeviceParam, LocaleParam, QueryParam

logger = getLogger(__name__)


@click.group(cls=Group)
def uf2() -> None:
    """Search and download CircuitPython UF2 binaries."""
    pass


uf2.command_class = Command


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
    with get_console().pager(styles=True):
        print(table)


@uf2.command
@argument("board", type=BoardParam(), required=True)
@argument("destination", type=click.Path(path_type=Path), required=False)
@option(
    "--locale",
    default="en_US",
    type=LocaleParam(),
    help="Locale for CircuitPython install.",
)
@option(
    "--offline/--no-offline",
    default=False,
    help="If ``True``, just print the download URL without actually downloading.",
)
def download(
    board: Board, locale: str, destination: Path | None, offline: bool
) -> Path:
    """
    Download CircuitPython image for the requested board.

    If ``DESTINATION`` is not provided, the file is downloaded to the current directory.

    If ``DESTINATION`` is a directory, the filename is automatically generated.
    """
    url = board.download_url(board.most_recent_version, locale)
    if offline:
        print(url)
        exit(0)
    destination = download_path(url, destination or Path.cwd())
    if destination.is_dir():
        destination /= url.split("/")[-1]
    print(f"Source: {url}")
    print(f"Destination: {destination}")

    cache = RequestCache()
    if url in cache:
        logger.info("Serving request from cache.")
        destination.write_bytes(cache[url])
        return destination

    logger.info("Populating cache from upstream.")
    response = urlopen(url)
    data = bytes()
    with progress.wrap_file(
        response,
        total=int(response.headers["Content-Length"]),
        description="Downloading",
    ) as response:
        while chunk := response.read(4 * 1024):
            data += chunk
    cache[url] = data
    destination.write_bytes(data)
    return destination


@uf2.command("devices", linux_only=True)
def uf2_devices() -> None:
    """List connected devices that are in UF2 bootloader mode."""
    devices = Uf2Device.all()
    if devices:
        print("Connected UF2 bootloader devices:", uf2_devices_table(devices))
    else:
        print(":person_shrugging: [blue]No[/] connected UF2 bootloader devices found.")


@uf2.command
@click.pass_context
@option(
    "--image_path",
    "-i",
    type=click.Path(path_type=Path, dir_okay=False, exists=True),
    help="If specified, install this already-existing UF2 image.",
)
@option(
    "--board",
    "-b",
    type=BoardParam(),
    help="If specified, automatically download and install appropriate CircuitPython UF2 image "
    "for this board ID.",
)
@option(
    "--device",
    "-d",
    "query",
    type=QueryParam(),
    help="If specified, this device will be restarted into its UF2 bootloader and "
    "be used as the target device for installing the image.",
)
@option(
    "--locale",
    default="en_US",
    type=LocaleParam(),
    help="Locale for CircuitPython install. Not used if an explicit image is given "
    "using ``--image_path``.",
)
@option(
    "--delete-download/--no-delete-download",
    default=True,
    help="Delete any downloaded UF2 images on exit.",
)
def install(
    context: click.Context,
    image_path: Path | None,
    board: Board | None,
    query: Query | None,
    locale: str,
    delete_download: bool,
) -> None:
    """
    Install a UF2 image onto a connected UF2 bootloader device.

    If a CircuitPython device is specified with ``--device``, then we restart that
    device into its UF2 bootloader and install the image onto it. If ``--device``
    is not specified, we assume there is already a connected UF2 bootloader device.
    """
    if not image_path and not board:
        print(
            "👎 Must specify [red]at least one[/] of: "
            "[blue]--image_path[/], [blue]--board[/]"
        )
        exit(1)
    if image_path and board:
        print(
            "👎 [red]Conflicting[/] options: "
            "[blue]--image_path[/] and [blue]--board[/]"
        )
        exit(1)
    if board:
        # Download UF2 image for this board.
        temp_dir = context.with_resource(temporary_directory(delete=delete_download))
        image_path = context.invoke(
            download, board=board, locale=locale, destination=temp_dir
        )

    # At this point image_path should either have been specified by the user or
    # automatically generated.
    assert image_path

    if query:
        device = distinct_device(query)
        print(
            "Restarting the following CircuitPython device into UF2 bootloader: ",
            device,
        )
        uf2_device = enter_uf2_bootloader(device)
    else:
        uf2_device = distinct_uf2_device()

    print("Selected UF2 bootloader device: ", uf2_device)
    mountpoint = uf2_device.mount_if_needed()
    destination = mountpoint / image_path.name

    print("Source: ", image_path)
    print("Destination: ", destination)

    output_file = destination.open("wb")
    with progress.open(str(image_path), "rb", description="Flashing") as input_file:
        while chunk := input_file.read(1024):
            output_file.write(chunk)
    with get_console().status("Closed destination file. Waiting for copy to complete."):
        output_file.close()
    print("Install complete.")
    # TODO(dhrosa): Show user status of newly setup device


@uf2.command("enter", linux_only=True)
@argument("device", type=DeviceParam(), required=True)
def uf2_enter(device: Device) -> None:
    """Restart selected device into UF2 bootloader."""
    print("Selected CircuitPython device: ", device)
    try:
        uf2_device = enter_uf2_bootloader(device)
    except KeyboardInterrupt:
        print("Wait [magenta]cancelled[/magenta] by keyboard interrupt.")
        return
    print("UF2 bootloader device: ", uf2_device)


@uf2.command("exit", linux_only=True)
@click.pass_context
def uf2_exit(context: click.Context) -> None:
    """Restart given UF2 bootloader device into normal application code."""
    with static_uf2_image_path("uf2_exit.uf2") as image_path:
        context.invoke(install, image_path=image_path)


@uf2.command(linux_only=True)
@argument("device", type=DeviceParam(), required=True)
def boot_info(device: Device) -> None:
    """Lookup UF2 bootloader info of the specified CircuitPython device."""
    print("Selected CircuitPython device: ", device)
    boot_info = device.get_boot_info()
    print("Version: ", boot_info.version)
    print("Board ID: ", boot_info.board_id)


@uf2.command("mount", linux_only=True)
def uf2_mount() -> None:
    """Mount connected UF2 bootloader device if needed and print the mountpoint."""
    device = distinct_uf2_device()
    print(device)
    mountpoint = device.get_mountpoint()
    if mountpoint:
        print(f"Device already mounted at {mountpoint}.")
        return
    mountpoint = device.mount_if_needed()
    print(f"Device mounted at {mountpoint}")


@uf2.command("unmount", linux_only=True)
def uf2_unmount() -> None:
    """Unmount connected UF2 bootloader device if needed."""
    device = distinct_uf2_device()
    print(device)
    mountpoint = device.get_mountpoint()
    if not mountpoint:
        print("Device already not mounted.")
        return
    print(f"Device is currently mounted at {mountpoint}")
    device.unmount_if_needed()
    print("Device unmounted.")


@uf2.command(linux_only=True)
@click.pass_context
def nuke(context: click.Context) -> None:
    """Clear out flash memory on UF2 bootloader device."""
    if not Confirm.ask(
        "This UF2 file will reset the flash storage on your device.\n"
        "This UF2 likely works on most RP2040-based boards.\n"
        "Do you want to continue?"
    ):
        print("[yellow]Cancelling[/]")
        exit(1)

    with static_uf2_image_path("flash_nuke.uf2") as image_path:
        context.invoke(install, image_path=image_path)


@uf2.command
@argument("image_path", type=click.Path(path_type=Path, dir_okay=False), required=True)
def analyze(image_path: Path) -> None:
    """
    Print details of each block in a UF2 image.

    If run in an interactive terminal, you can use arrow keys to browse blocks.
    If not run in an interactive context, the information about every block is
    printed.
    """

    raw = image_path.read_bytes()
    blocks = list(Block.from_bytes_multi(raw))
    index = 0

    # Non-interactive; print all the blocks.
    if not stdout.isatty():
        for block in blocks:
            print(block)
        exit()

    bindings = {
        "q": "quit",
        "left/up": "previous block",
        "right/down": "next block",
        "page_up": "back 16 blocks",
        "page_down": "forward 16 blocks",
        "home": "first block",
        "end": "final block",
    }
    help_text = " | ".join(
        f"[blue]{key}[/]: {label}" for key, label in bindings.items()
    )

    def renderable() -> RichGroup:
        return RichGroup(
            Pretty(blocks[index]),
            help_text,
        )

    with Live(renderable(), auto_refresh=False) as live:
        while True:
            match readkey():
                case key.UP | key.LEFT:
                    index -= 1
                case key.DOWN | key.RIGHT:
                    index += 1
                case key.PAGE_UP:
                    index -= 16
                case key.PAGE_DOWN:
                    index += 16
                case key.HOME:
                    index = 0
                case key.END:
                    index = -1
                case "q" | key.ESC:
                    break
                case x:
                    print(x)
            index %= len(blocks)
            live.update(renderable(), refresh=True)


def download_path(url: str, destination: Path) -> Path:
    """
    Determine the destination file path for the download.

    If `destination` is already a file path, it is returned unchanged. If
      `destination` is a directory, the file name is derived from the URL.
    """
    if destination.is_dir():
        return destination / url.split("/")[-1]
    return destination


def enter_uf2_bootloader(device: Device) -> Uf2Device:
    """Restarts the given device into its UF2 bootloader, and returns the resulting Uf2Device."""
    if uf2_devices := Uf2Device.all():
        print(
            ":thumbs_down: UF2 bootloader device(s) [red]already connected[/]: ",
            uf2_devices_table(uf2_devices),
        )
        exit(1)

    device.uf2_enter()

    start_time = time.time()

    def elapsed_str() -> str:
        return naturaldelta(time.time() - start_time)

    with get_console().status("Waiting for device restart") as status:
        while True:
            status.update(f"Waiting for device restart. Elapsed time: {elapsed_str()}")
            uf2_devices = Uf2Device.all()
            if not uf2_devices:
                time.sleep(0.1)
                continue
            if len(uf2_devices) > 1:
                print("[red]Multiple[/] UF2 bootloader devices appeared.")
                exit(1)
            # One connected device.
            uf2_device = next(iter(uf2_devices))
            print(
                f":thumbs_up: [green]Successfully[/] entered UF2 bootloader "
                f"in elapsed time of {elapsed_str()}."
            )
            return uf2_device


@contextmanager
def temporary_directory(delete: bool) -> Iterator[Path]:
    """Automatically create an empty directory and yield it.

    If `delete` is True, the directory is automatically deleted on exit.
    """
    path = Path(mkdtemp())
    try:
        yield path
    finally:
        if delete:
            logger.debug(f"Deleting temporary directory: {path}")
            rmtree(path)


@contextmanager
def static_uf2_image_path(file_name: str) -> Iterator[Path]:
    """Context manager yielding a (possibly temporary) path to a bundled UF2 image."""
    with resources.as_file(resources.files(static).joinpath(file_name)) as image_path:
        yield image_path
