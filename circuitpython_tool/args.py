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
        "--fuzzy",
        "-f",
        type=str,
        default="",
        help="Filter to devices whose vendor, model, or serial contains this string.",
    )
    parser.add_argument(
        "--preset",
        "-p",
        type=str,
        default="",
        dest="preset_name",
    )


def add_watch_arg(parser):
    parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Continuously upload code as files in the source directories change.",
    )


def parse_args():
    """Parse command line arguments."""
    parser = ArgumentParser()

    # Subcommand parsers.
    subparsers = parser.add_subparsers(title="commands", required=True, dest="command")

    list_parser = subparsers.add_parser(
        "list",
        help="List all CircuitPython devices matching the requested filters.",
    )
    add_filter_args(list_parser)

    upload_parser = subparsers.add_parser("upload", help="Upload code to device.")
    add_filter_args(upload_parser)
    add_watch_arg(upload_parser)
    upload_parser.add_argument(
        "source_dir",
        type=Path,
        nargs="+",
        help="Source directory to copy.",
    )
    upload_parser.add_argument(
        "--save-preset",
        type=str,
        default="",
        help="Save the selected device and source directory set as a preset that can be later recalled using preset_upload.",
    )

    preset_upload_parser = subparsers.add_parser(
        "preset_upload",
        help="Similar to the 'upload' command, but using parameters from a preset.",
    )
    add_watch_arg(preset_upload_parser)
    preset_upload_parser.add_argument("preset_name", type=str)

    connect_parser = subparsers.add_parser(
        "connect", help="Connect to device's serial console."
    )
    add_filter_args(connect_parser)

    preset_connect_parser = subparsers.add_parser(
        "preset_connect",
        help="Similar to the 'connect' command, but using parameters from a preset.",
    )
    preset_connect_parser.add_argument("preset_name", type=str)

    # Ensure these attributes are set even if the relevant commands aren't specified.
    parser.set_defaults(
        source_dir=[],
        watch=False,
        save_preset="",
        vendor="",
        model="",
        serial="",
        fuzzy="",
        preset_name="",
    )

    return parser.parse_args()
