"""Visualization of CLI command structure."""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, cast

import rich_click as click
from click import Context
from rich import get_console, print
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.tree import Tree

from .cli import commands

THEME = Theme(
    {
        "param.path": "blue",
        "param.string": "yellow",
        "param.bool": "green",
    }
)


@dataclass(frozen=True)
class Parameter:
    name: str
    required: bool
    raw_param_type: str
    raw_default: Any
    # TODO(dhrosa): This doesn't actually appear in the command metadata for some reason.
    envvar: str | None

    @property
    def param_type(self) -> str:
        match self.raw_param_type:
            case "ConfigStorageParam" | "FakeDeviceParam":
                return "Path"
            case "Choice" | "QueryOrLabelParam" | "LocaleParam" | "BoardParam":
                return "String"
            case x:
                return x

    @property
    def param_type_style(self) -> str:
        return f"param.{self.param_type.lower()}"

    @property
    def default(self) -> str | None:
        if self.raw_default is None:
            return None
        if self.raw_param_type == "ConfigStorageParam":
            return str(self.raw_default.path)
        if self.raw_param_type == "QueryOrLabelParam":
            return str(self.raw_default.as_str())
        return str(self.raw_default)


@dataclass(frozen=True)
class Argument(Parameter):
    @staticmethod
    def from_dict(p: dict[str, Any]) -> "Argument":
        return Argument(
            p["name"],
            required=p["required"],
            raw_param_type=p["type"]["param_type"],
            raw_default=p["default"],
            envvar=p["envvar"],
        )

    def render(self) -> Text:
        t = Text.styled(self.name.upper(), style="bold")
        if self.default:
            t.append(f" (default: {self.default})")
        if self.envvar:
            t.append(f" (envvar: {self.envvar}")
        t.stylize(self.param_type_style)
        if not self.required:
            t = Text.assemble("[", t, "]")
        return t


@dataclass(frozen=True)
class Option(Parameter):
    opts: list[str]
    is_flag: bool

    @staticmethod
    def from_dict(p: dict[str, Any]) -> "Option":
        return Option(
            name=p["name"],
            required=p["required"],
            raw_param_type=p["type"]["param_type"],
            raw_default=p["default"],
            opts=p["opts"],
            is_flag=p["is_flag"],
            envvar=p["envvar"],
        )

    def render(self) -> Text:
        t = Text.styled(self.opts[0], style="bold")
        if not self.is_flag:
            t.append(" " + self.name, style="italic")
        if self.default:
            t.append(f" (default: {self.default})")
        if self.envvar:
            t.append(f" (envvar: {self.envvar}")
        t.stylize(self.param_type_style)
        if not self.required:
            t = Text.assemble("[", t, "]")
        return t


@dataclass
class Node:
    name: str
    arguments: list[Argument]
    options: list[Option]
    children: list["Node"]

    @property
    def parameters(self) -> Sequence[Parameter]:
        return cast(list[Parameter], self.arguments) + cast(
            list[Parameter], self.options
        )

    def to_tree(self, tree: Tree | None = None) -> Tree:
        label: Panel | str
        if self.arguments or self.options:
            label = Panel.fit(Text("\n").join(self.contents()), title=self.name)
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

    def contents(self) -> Iterator[Text]:
        if self.arguments:
            yield Text(" ").join([a.render() for a in self.arguments])
        for o in self.options:
            yield o.render()


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
    get_console().push_theme(THEME)


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
