"""
Shell completion functions for custom `click` parameters.
"""

# TODO(dhrosa): Merge this into params.py

import logging

from click import Context, Parameter
from click.shell_completion import CompletionItem

from ..hw.real_device import RealDevice
from .shared_state import SharedState


def disable_logging() -> None:
    # Logging interferes with shell output
    logging.disable(logging.CRITICAL)


def device_label(
    context: Context, param: Parameter, incomplete: str
) -> list[CompletionItem]:
    """Shell completion for device labels."""
    disable_logging()
    config_storage = context.ensure_object(SharedState).config_storage
    completions: list[CompletionItem] = []
    with config_storage.open() as config:
        for key, label in config.device_labels.items():
            completions.append(
                CompletionItem(key, help="Query: " + label.query.as_str())
            )
    return completions


def query(context: Context, param: Parameter, incomplete: str) -> list[CompletionItem]:
    disable_logging()
    return [
        CompletionItem(":".join((d.vendor, d.model, d.serial)))
        for d in RealDevice.all()
    ]


def label_or_query(
    context: Context, param: Parameter, incomplete: str
) -> list[CompletionItem]:
    """Shell completion for device labels or queries."""
    disable_logging()
    completions: list[CompletionItem] = []
    config_storage = context.ensure_object(SharedState).config_storage
    with config_storage.open() as config:
        for name, label in config.device_labels.items():
            completions.append(
                CompletionItem(name, help=f"Label for query {label.query.as_str()}")
            )
    completions.extend(query(context, param, incomplete))
    return completions
