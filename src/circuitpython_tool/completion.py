import logging
from typing import Any

from click import Context, Parameter
from click.shell_completion import CompletionItem

from .real_device import all_devices
from .shared_state import SharedState


def disable_logging() -> None:
    # Logging interferes with shell output
    logging.disable(logging.CRITICAL)


def all_context_params(context: Context | None) -> dict[str, Any]:
    """Union of recognized parameters from context and all of its ancestors."""
    params: dict[str, Any] = {}
    while context is not None:
        params |= context.params
        context = context.parent
    return params


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
        CompletionItem(":".join((d.vendor, d.model, d.serial))) for d in all_devices()
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


def source_tree(
    context: Context, param: Parameter, incomplete: str
) -> list[CompletionItem]:
    disable_logging()
    """Shell completion for source trees."""
    completions: list[CompletionItem] = []
    config_storage = context.ensure_object(SharedState).config_storage
    with config_storage.open() as config:
        for key, tree in config.source_trees.items():
            completions.append(
                CompletionItem(
                    key,
                    help="Source paths: "
                    + " | ".join(str(p) for p in tree.source_dirs),
                )
            )
    return completions
