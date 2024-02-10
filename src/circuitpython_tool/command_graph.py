"""Visualization of CLI command structure."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import rich_click as click
from click import Context
from rich import get_console, print
from rich.panel import Panel
from rich.tree import Tree

from .cli import commands


@dataclass
class Argument:
    name: str
    required: bool

    @staticmethod
    def from_dict(p: dict[str, Any]) -> "Argument":
        return Argument(
            p["name"],
            required=p["required"],
        )

    def render(self) -> str:
        s = self.name.upper()
        if not self.required:
            s = f"[{s}]"
        return s


@dataclass
class Option:
    name: str
    opts: list[str]
    required: bool

    @staticmethod
    def from_dict(p: dict[str, Any]) -> "Option":
        return Option(
            name=p["name"],
            opts=p["opts"],
            required=p["required"],
        )

    def render(self) -> str:
        return self.opts[0]


@dataclass
class Node:
    name: str
    children: list["Node"]
    arguments: list[Argument]
    options: list[Option]

    def to_tree(self, tree: Tree | None = None) -> Tree:
        label: Any
        if self.arguments or self.options:
            label = Panel.fit("".join(self.contents()), title=self.name)
        else:
            label = self.name

        if tree is None:
            tree = Tree(label)
            subtree = tree
        else:
            subtree = tree.add(label)

        for child in self.children:
            child.to_tree(subtree)
        return tree

    def param_strings(self) -> Iterator[str]:
        for a in self.arguments:
            yield a.render()
        for o in self.options:
            yield o.render()

    def contents(self) -> Iterator[str]:
        yield " ".join(self.param_strings())


def to_node(command: dict[str, Any]) -> Node:
    params = [p for p in command["params"] if p["name"] != "help"]
    return Node(
        name=command["name"],
        children=[to_node(i) for i in command.get("commands", {}).values()],
        options=[
            Option.from_dict(p) for p in params if p["param_type_name"] == "option"
        ],
        arguments=[
            Argument.from_dict(p) for p in params if p["param_type_name"] == "argument"
        ],
    )


def commands_context() -> Context:
    return click.Context(commands.main)


@click.group
def main() -> None:
    pass


@main.command
def raw() -> None:
    with get_console().pager(styles=True), commands_context() as context:
        print(context.to_info_dict())


@main.command
def nodes() -> None:
    with get_console().pager(styles=True), commands_context() as context:
        print(to_node(context.to_info_dict()["command"]))


@main.command
def tree() -> None:
    with commands_context() as context:
        root = to_node(context.to_info_dict()["command"])
    print(root.to_tree())


if __name__ == "__main__":
    main()
