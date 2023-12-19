import logging
import shutil
from collections.abc import Iterable
from os import execlp
from pathlib import Path
from sys import exit
from typing import Any, Optional

import rich_click as click
from rich import get_console, print, traceback
from rich.logging import RichHandler
from rich.table import Table

from .config import Config, ConfigStorage, DeviceLabel, SourceTree
from .device import Device, Query, all_devices, matching_devices
from .fs import walk_all, watch_all

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


class QueryParam(click.ParamType):
    name = "query"

    def convert(self, value: str, param: Any, context: Any) -> Query:
        try:
            return Query.parse(value)
        except Query.ParseError as error:
            self.fail(str(error))


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "--config",
    "-c",
    "config_path",
    type=Path,
    default=None,
    help="Path to configuration TOML file for device labels and source trees.",
)
@click.pass_context
def run(context: click.Context, config_path: Optional[Path]) -> None:
    """Tool for interfacing with CircuitPython devices."""
    context.obj = ConfigStorage(config_path)


@run.command()
@click.argument("query", type=QueryParam(), default="")
def devices(query: Query) -> None:
    """List all connected CircuitPython devices.

    If QUERY is specified, only devices matching that query are listed."""
    devices = matching_devices(query)
    if not devices:
        print(":person_shrugging: [blue]No[/] connected CircuitPython devices found.")
        return
    print("Connected CircuitPython devices:", devices_table(devices))


@run.group()
def label() -> None:
    """Manage device labels."""
    pass


@label.command("list")
@click.pass_obj
def label_list(config_storage: ConfigStorage) -> None:
    """List all device labels."""
    with config_storage.open() as config:
        labels = config.device_labels
    if not labels:
        print(":person_shrugging: [blue]No[/] existing labels found.")
        return
    table = Table("Label", "Query")
    for name, label in config.device_labels.items():
        table.add_row(name, label.query.as_str())
    print(table)


@label.command("add")
@click.argument("key", required=True)
@click.argument("query", type=QueryParam(), required=True)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Add the new label even if a label with the same name already exists."
    "The new QUERY value will override the previous stored value.",
)
@click.pass_obj
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
@click.argument("label_name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Return success even if there was no matching label to remove.",
)
@click.pass_obj
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


@run.group()
def tree() -> None:
    """Manage source trees."""
    pass


@tree.command("list")
@click.pass_obj
def tree_list(config_storage: ConfigStorage) -> None:
    """List all source trees."""
    with config_storage.open() as config:
        trees = config.source_trees
    if not trees:
        print(":person_shrugging: [blue]No[/] existing source trees found.")
        return
    table = Table("Name", "Source Directories")
    for name, tree in trees.items():
        table.add_row(name, "\n".join(str(p) for p in tree.source_dirs))
    print(table)


@tree.command("add")
@click.argument("key", required=True)
@click.argument("source_dirs", type=Path, required=True, nargs=-1)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Add the new tree even if a tree with the same name already exists."
    "The new SOURCE_DIRS will override the previous stored value.",
)
@click.pass_obj
def tree_add(
    config_storage: ConfigStorage, key: str, source_dirs: list[Path], force: bool
) -> None:
    """Add a new source tree.

    Creates a new source tree with the name KEY, pointing to the paths listed in
    SOURCE_DIRS.

    The children of each of SOURCE_DIRS will be copied to the device;
    effectively a union of the children.

    """
    with config_storage.open() as config:
        trees = config.source_trees
        old_tree = trees.get(key)
        if old_tree:
            if force:
                logger.info(
                    f"Source tree [blue]{key}[/] already exists. Proceeding anyway."
                )
            else:
                print(
                    f":thumbs_down: Source tree [red]{key}[/] already exists: ",
                    old_tree,
                )
                exit(1)

        tree = SourceTree(source_dirs)
        trees[key] = tree
    print(
        f":thumbs_up: Source tree [blue]{key}[/] added [green]successfully[/]:\n{tree}"
    )


@tree.command("remove")
@click.confirmation_option(
    "--yes", "-y", prompt="Are you sure you want to delete this source tree?"
)
@click.argument("key")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Return success even if there was no matching source tree to remove.",
)
@click.pass_obj
def tree_remove(config_storage: ConfigStorage, key: str, force: bool) -> None:
    """Delete a source tree.

    This command just deletes our internal reference to the source paths. This
    command does not change the contents of the source paths.

    """
    with config_storage.open() as config:
        tree = config.source_trees.get(key)
        if tree:
            logger.debug(f"Found source tree [blue]{key}[/]: {tree}")
            del config.source_trees[key]
        elif force:
            logger.info(f"Source tree [blue]{key}[/] not found. Proceeding anyway.")
        else:
            print(f":thumbs_down: Source tree [red]{key}[/] does not exist.")
            exit(1)
    print(f":thumbs_up: Source tree [blue]{key}[/] [green]successfully[/] deleted.")


def get_tree_and_label(
    config: Config, tree_name: str, label_name: str
) -> tuple[SourceTree, DeviceLabel]:
    try:
        tree = config.source_trees[tree_name]
    except KeyError:
        print(f":thumbs_down: Source tree [red]{tree_name}[/] does not exist.")
        exit(1)

    try:
        label = config.device_labels[label_name]
    except KeyError:
        print(f":thumbs_down: Label [red]{label_name}[/] does not exist.")
        exit(1)
    return (tree, label)


@run.command("upload")
@click.argument("tree_name", required=True)
@click.argument("label_name", required=True)
@click.pass_obj
def upload_command(
    config_storage: ConfigStorage, tree_name: str, label_name: str
) -> None:
    """Upload code to device.

    The contents of the source tree TREE_NAME will be copied onto the device
    with the label LABEL_NAME
    """
    with config_storage.open() as config:
        tree, label = get_tree_and_label(config, tree_name, label_name)
    device = distinct_device(label.query)
    mountpoint = device.mount_if_needed()
    print("Uploading to device: ", device)
    upload(tree.source_dirs, mountpoint)
    print(":thumbs_up: Upload [green]succeeded.")


@run.command
@click.argument("tree_name", required=True)
@click.argument("label_name", required=True)
@click.pass_obj
def watch(config_storage: ConfigStorage, tree_name: str, label_name: str) -> None:
    """Continuously upload code to device in response to source file changes.

    The contents of the source tree TREE_NAME will be copied onto the device
    with the label LABEL_NAME.

    This command will always perform at least one upload. Then this command
    waits for filesystem events from all paths and descendant paths of the
    source tree. Currently this command will only properly track file
    modifications. Creation of new files and folders requires you to rerun this
    command in order to monitor them.
    """
    with config_storage.open() as config:
        tree, label = get_tree_and_label(config, tree_name, label_name)
    device = distinct_device(label.query)
    mountpoint = device.mount_if_needed()
    print("Target device: ")
    print(device)
    # Always do at least one upload at the start.
    source_dirs = tree.source_dirs
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


@run.command
@click.argument("label_name", required=True)
@click.pass_obj
def connect(config_storage: ConfigStorage, label_name: str) -> None:
    """Connect to a device's serial terminal.

    LABEL_NAME is the label of a device query that was added by 'label add'.
    """
    with config_storage.open() as config:
        try:
            label = config.device_labels[label_name]
        except KeyError:
            print(f":thumbs_down: Label [red]{label_name}[/] does not exist.")
            exit(1)
    device = distinct_device(label.query)
    logger.info("Launching minicom for ")
    logger.info(device)
    assert device.serial_path is not None
    execlp("minicom", "minicom", "-D", str(device.serial_path))


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


def distinct_device(query: Query) -> Device:
    matching_devices = [d for d in all_devices() if query.matches(d)]
    match matching_devices:
        case [device]:
            return device
        case []:
            print(":thumbs_down: [red]0[/red] matching devices found.")
            print(all_devices())
            exit(1)
        case _:
            count = len(matching_devices)
            print(
                ":thumbs_down: Ambiguous filter. ",
                f"[red]{count}[/red] matching devices found:",
                devices_table(matching_devices),
            )
            exit(1)


def upload(source_dirs: Iterable[Path], mountpoint: Path) -> None:
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
