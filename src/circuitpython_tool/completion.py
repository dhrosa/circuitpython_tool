from typing import Any, Optional

from click import Context, Parameter
from click.shell_completion import CompletionItem

from .config import ConfigStorage


def all_context_params(context: Optional[Context]) -> dict[str, Any]:
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
    all_params = all_context_params(context)
    completions: list[CompletionItem] = []
    with ConfigStorage(all_params["config_path"]).open() as config:
        for key, label in config.device_labels.items():
            completions.append(
                CompletionItem(key, help="Query: " + label.query.as_str())
            )
    return completions


def source_tree(
    context: Context, param: Parameter, incomplete: str
) -> list[CompletionItem]:
    """Shell completion for source trees."""
    all_params = all_context_params(context)
    completions: list[CompletionItem] = []
    with ConfigStorage(all_params["config_path"]).open() as config:
        for key, tree in config.source_trees.items():
            completions.append(
                CompletionItem(
                    key,
                    help="Source paths: "
                    + " | ".join(str(p) for p in tree.source_dirs),
                )
            )
    return completions
