"""
Shell completion functions for custom `click` parameters.
"""

# TODO(dhrosa): Merge this into params.py

import logging

from click import Context, Parameter
from click.shell_completion import CompletionItem

from ..hw import RealDevice


def disable_logging() -> None:
    # Logging interferes with shell output
    logging.disable(logging.CRITICAL)


def query(context: Context, param: Parameter, incomplete: str) -> list[CompletionItem]:
    disable_logging()
    return [
        CompletionItem(":".join((d.vendor, d.model, d.serial)))
        for d in RealDevice.all()
    ]
