from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path

from .device import Query


def parse_query(arg: str) -> Query:
    """Parses a string of the format (vendor:model:serial) into a Query"""
    if not arg:
        return Query()
    parts = arg.split(":")
    if (count := len(parts)) != 3:
        raise ArgumentTypeError(f"Expected 3 query components. Instead found {count}")
    return Query(*parts)


def parse_args():
    """Parse command line arguments."""
    root = ArgumentParser()

    # Subcommand parsers.
    children = root.add_subparsers(title="commands", required=True, dest="command")

    devices = children.add_parser(
        "devices", help="List all connected CircuitPython devices."
    )
    devices.add_argument(
        "query",
        type=parse_query,
        nargs="?",
        default="::",
        help="Query in the format 'vendor:model:serial'.",
    )

    upload = children.add_parser("upload", help="Upload code to device.")
    upload.add_argument("preset_name", type=str)

    watch = children.add_parser(
        "watch", help="Upload code to device in response to filesystem events."
    )
    watch.add_argument("preset_name", type=str)

    connect = children.add_parser("connect", help="Connect to device's serial console.")
    connect.add_argument("preset_name", type=str)

    preset = children.add_parser("preset", help="Manipulate presets.")
    preset_children = preset.add_subparsers(
        title="preset commands", required=True, dest="preset_command"
    )

    preset_children.add_parser("list", help="List existing presets.")

    preset_save = preset_children.add_parser("save", help="Save preset.")
    preset_save.add_argument(
        "new_preset_name", type=str, help="Name of preset to save."
    )
    preset_save.add_argument(
        "source_dir", type=Path, nargs="+", help="Source directory to copy."
    )

    # Ensure these attributes are set even if the relevant commands aren't specified.
    root.set_defaults(
        source_dir=[],
        watch=False,
        new_preset_name="",
        vendor="",
        model="",
        serial="",
        preset_name="",
        preset_command="",
    )

    return root.parse_args()
