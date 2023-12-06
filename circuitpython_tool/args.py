from argparse import ArgumentParser
from pathlib import Path


def add_filter_args(parser):
    parser.add_argument(
        "--vendor",
        "-v",
        type=str,
        default="",
        help="Filter to devices whose vendor contains this string.",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default="",
        help="Filter to devices whose model contains this string.",
    )
    parser.add_argument(
        "--serial",
        "-s",
        type=str,
        default="",
        help="Filter to devices whose serial contains this string.",
    )
    parser.add_argument(
        "--preset",
        "-p",
        type=str,
        default="",
        dest="preset_name",
    )


def parse_args():
    """Parse command line arguments."""
    parser = ArgumentParser()

    # Subcommand parsers.
    subparsers = parser.add_subparsers(title="commands", required=True, dest="command")

    subparsers.add_parser("devices", help="List all connected CircuitPython devices.")

    upload_parser = subparsers.add_parser("upload", help="Upload code to device.")
    upload_parser.add_argument("preset_name", type=str)
    upload_parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Continuously upload code as files in the source directories change.",
    )

    connect_parser = subparsers.add_parser(
        "connect", help="Connect to device's serial console."
    )
    connect_parser.add_argument("preset_name", type=str)

    # New-style commands.
    preset_list_parser = subparsers.add_parser(
        "preset_list", help="List existing presets."
    )

    preset_save_parser = subparsers.add_parser(
        "preset_save", help="List existing presets."
    )
    preset_save_parser.add_argument(
        "new_preset_name", type=str, help="Name of preset to save."
    )
    add_filter_args(preset_save_parser)
    preset_save_parser.add_argument(
        "source_dir",
        type=Path,
        nargs="+",
        help="Source directory to copy.",
    )

    # Ensure these attributes are set even if the relevant commands aren't specified.
    parser.set_defaults(
        source_dir=[],
        watch=False,
        new_preset_name="",
        vendor="",
        model="",
        serial="",
        fuzzy="",
        preset_name="",
    )

    return parser.parse_args()
