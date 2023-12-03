from argparse import ArgumentParser
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = ArgumentParser()

    # Common flags between subcommands.
    filter_group = parser.add_mutually_exclusive_group()
    filter_group.add_argument(
        "--vendor",
        type=str,
        default="",
        help="Filter to devices whose vendor contains this string.",
    )
    filter_group.add_argument(
        "--model",
        type=str,
        default="",
        help="Filter to devices whose model contains this string.",
    )
    filter_group.add_argument(
        "--serial",
        type=str,
        default="",
        help="Filter to devices whose serial contains this string.",
    )
    filter_group.add_argument(
        "--fuzzy",
        type=str,
        default="",
        help="Filter to devices whose vendor, model, or serial contains this string.",
    )
    filter_group.add_argument(
        "--preset",
        type=str,
        default="",
        dest="preset_name",
    )

    # Subcommand parsers.
    subparsers = parser.add_subparsers(required=True, dest="command")

    subparsers.add_parser(
        "list", help="List all CircuitPython devices matching the requested filters."
    )

    upload_parser = subparsers.add_parser("upload", help="Upload code to device.")
    upload_parser.add_argument(
        "source_dir",
        type=Path,
        nargs="+",
        help="Source directory to copy.",
    )
    upload_parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously upload code as files in the source directories change.",
    )
    upload_parser.add_argument(
        "--save-preset",
        type=str,
        default="",
        help="Save the selected device and source directory set as a preset that can be later recalled using preset_upload.",
    )
    # Ensure these attributes are set even if the upload command isn't
    # specified.
    parser.set_defaults(source_dir=[], watch=False, save_preset="")

    preset_upload_parser = subparsers.add_parser(
        "preset_upload",
        help="Similar to the 'upload' command, but using parameters from a preset.",
    )
    preset_upload_parser.add_argument("preset_name", type=str)

    subparsers.add_parser("connect", help="Connect to device's serial console.")

    return parser.parse_args()
