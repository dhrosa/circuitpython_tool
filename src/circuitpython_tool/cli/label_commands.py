"""'label' subcommands."""

from logging import getLogger

import rich_click as click
from rich import print
from rich.table import Table

from ..hw.query import Query
from . import completion, pass_config_storage, pass_read_only_config
from .config import Config, ConfigStorage, DeviceLabel
from .params import label_or_query_argument

logger = getLogger(__name__)


@click.group()
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
