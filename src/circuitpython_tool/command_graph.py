"""Visualization of CLI command structure."""

from dataclasses import dataclass
from typing import Any

from click import Context
from rich import print
from rich.tree import Tree

from .cli import commands


@dataclass
class Node:
    name: str
    children: list["Node"]

    def to_tree(self, tree: Tree | None = None) -> Tree:
        if tree is None:
            tree = Tree("commands", hide_root=True)
        subtree = tree.add(self.name)
        for child in self.children:
            child.to_tree(subtree)
        return tree


def to_node(command: dict[str, Any]) -> Node:
    return Node(
        name=command["name"],
        children=[to_node(i) for i in command.get("commands", {}).values()],
    )


if __name__ == "__main__":
    with Context(commands.main) as context:
        root = to_node(context.to_info_dict()["command"])
    print(root.to_tree())
