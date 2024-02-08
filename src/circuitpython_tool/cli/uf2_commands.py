"""'uf2' subcommands."""

import time
from logging import getLogger
from pathlib import Path
from tempfile import mkdtemp
from typing import cast
from urllib.request import urlopen

import rich_click as click
from humanize import naturaldelta
from rich import get_console, print, progress
from rich.table import Table

from ..hw.device import Device
from ..hw.query import Query
from ..hw.uf2_device import Uf2Device
from ..uf2 import Board
from . import distinct_device, distinct_uf2_device, uf2_devices_table
from .params import BoardParam, LocaleParam, label_or_query_argument

logger = getLogger(__name__)


@click.group
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
def download(board: Board, locale: str, destination: Path) -> Path:
    """Download CircuitPython image for the requested board.

    If DESTINATION is not provided, the file is downloaded to the current directory.
    If DESTINATION is a directory, the filename is automatically generated.
    """
    url = board.download_url(board.most_recent_version, locale)
    destination = download_path(url, destination)
    if destination.is_dir():
        destination /= url.split("/")[-1]
    print(f"Source: {url}")
    print(f"Destination: {destination}")

    response = urlopen(url)
    with (
        progress.wrap_file(
            response,
            total=int(response.headers["Content-Length"]),
            description="Downloading",
        ) as response,
        destination.open("wb") as output,
    ):
        while chunk := response.read(4 * 1024):
            output.write(chunk)
    return destination


@uf2.command
@click.pass_context
@label_or_query_argument("query", required=True)
@click.argument(
    "destination", type=click.Path(path_type=Path), required=False, default=Path.cwd()
)
@click.option(
    "--locale",
    default="en_US",
    type=LocaleParam(),
    help="Locale for CircuitPython install.",
)
def auto_download(
    context: click.Context, query: Query, locale: str, destination: Path
) -> Path:
    """Download the appropriate CircuitPython image for the selected CircuitPython device.

    Automatically detects the Adafruit board ID of the connected device and
    downloads the respective CircuitPython distribution.

    If DESTINATION is not provided, the file is downloaded to the current directory.
    If DESTINATION is a directory, the filename is automatically generated.
    """
    device = distinct_device(query)
    print("Selected CircuitPython device: ", device)

    board_id = device.get_boot_info().board_id
    print("Device board ID: ", board_id)
    board = Board.by_id(board_id)

    return cast(
        Path,
        context.invoke(download, board=board, locale=locale, destination=destination),
    )


@uf2.command
@click.argument(
    "image_path",
    type=click.Path(path_type=Path, dir_okay=False, exists=True),
    required=True,
)
@label_or_query_argument("query")
def install(image_path: Path, query: Query | None) -> None:
    """Install the given UF2 image onto connected UF2 bootloader device.

    If a CircuitPython device is not specified, we assume there is already a
    connected UF2 bootloader device to use as the target.

    If a CircuitPython device is specified, it is restarted into its UF2
    bootloader and is used as the target.
    """
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

    try:
        output_file = destination.open("wb")
        with progress.open(str(image_path), "rb", description="Flashing") as input_file:
            while chunk := input_file.read(1024):
                output_file.write(chunk)
    finally:
        with get_console().status(
            "Closed destination file. Waiting for copy to complete."
        ):
            output_file.close()
    print("Install complete.")


@uf2.command
@click.pass_context
@label_or_query_argument("query", required=True)
@click.option(
    "--locale",
    default="en_US",
    type=LocaleParam(),
    help="Locale for CircuitPython install.",
)
@click.option(
    "--delete-download/--no-delete-download",
    default=True,
    help="Delete downloaded UF2 image on exit.",
)
def auto_install(
    context: click.Context, query: Query, locale: str, delete_download: bool
) -> None:
    """Automatically detect the appropriate CircuitPython distribution and install it."""
    temp_dir = Path(mkdtemp("-circuitpython-tool-uf2-download"))
    image_path: Path | None = None
    try:
        device = distinct_device(query)
        image_path = context.invoke(
            auto_download, query=query, locale=locale, destination=temp_dir
        )
        enter_uf2_bootloader(device)
        context.invoke(install, query=None, image_path=image_path)
    finally:
        if delete_download:
            if image_path:
                logger.debug(f"Deleting {image_path}")
                image_path.unlink()
            logger.debug(f"Deleting {temp_dir}")
            temp_dir.rmdir()
        else:
            logger.debug("Keeping temporary download file.")


@uf2.command
@label_or_query_argument("query", required=True)
def restart(query: Query) -> None:
    """Restart selected device into UF2 bootloader."""
    device = distinct_device(query)
    print("Selected CircuitPython device: ", device)
    try:
        uf2_device = enter_uf2_bootloader(device)
    except KeyboardInterrupt:
        print("Wait [magenta]cancelled[/magenta] by keyboard interrupt.")
        return
    print("UF2 bootloader device: ", uf2_device)


@uf2.command("devices")
def uf2_devices() -> None:
    """List connected devices that are in UF2 bootloader mode."""
    devices = Uf2Device.all()
    if devices:
        print("Connected UF2 bootloader devices:", uf2_devices_table(devices))
    else:
        print(":person_shrugging: [blue]No[/] connected UF2 bootloader devices found.")


@uf2.command("mount")
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


@uf2.command("unmount")
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


@uf2.command
@label_or_query_argument("query", required=True)
def boot_info(query: Query) -> None:
    """Lookup UF2 bootloader info of the specified CircuitPython device."""
    device = distinct_device(query)
    print("Selected CircuitPython device: ", device)
    boot_info = device.get_boot_info()
    print("Version: ", boot_info.version)
    print("Board ID: ", boot_info.board_id)


def download_path(url: str, destination: Path) -> Path:
    """Determine the destination file path for the download.

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
