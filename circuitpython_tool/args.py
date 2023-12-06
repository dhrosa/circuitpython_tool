from argparse import ArgumentParser
from pathlib import Path


def add_fake_arg(parser):
    parser.add_argument(
        "--fake",
        dest="fake_device_count",
        type=int,
        help="If set, generate this many fake devices rather than probing for real devices.",
    )


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
    add_fake_arg(list_parser)
    add_filter_args(list_parser)

    upload_parser = subparsers.add_parser("upload", help="Upload code to device.")
    add_fake_arg(upload_parser)
    add_watch_arg(upload_parser)
    upload_parser.add_argument("preset_name", type=str)

    connect_parser = subparsers.add_parser(
        "connect", help="Connect to device's serial console."
    )
    add_fake_arg(connect_parser)
    connect_parser.add_argument("preset_name", type=str)

    # New-style commands.
    preset_list_parser = subparsers.add_parser(
        "preset_list", help="List existing presets."
    )
    add_fake_arg(preset_list_parser)

    preset_save_parser = subparsers.add_parser(
        "preset_save", help="List existing presets."
    )
    preset_save_parser.add_argument(
        "new_preset_name", type=str, help="Name of preset to save."
    )
    add_fake_arg(preset_save_parser)
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
