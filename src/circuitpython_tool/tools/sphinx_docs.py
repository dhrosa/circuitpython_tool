import textwrap
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

import rich_click as click

from ..cli import commands

dedent = textwrap.dedent

Lines: TypeAlias = Iterable[str]


def indent(s: str) -> str:
    return textwrap.indent(s, " " * 3)


def indent_lines(lines: Lines) -> Lines:
    for line in lines:
        yield indent(line)


@dataclass
class Parameter:
    name: str
    help: str
    required: bool

    def canonical_form(self) -> str:
        raise NotImplementedError

    @property
    def inline_form(self) -> str:
        form = self.canonical_form()
        if not self.required:
            form = f"[{form}]"
        return form


@dataclass
class Argument(Parameter):
    @staticmethod
    def from_dict(p: dict[str, Any]) -> "Argument":
        return Argument(
            p["name"],
            help="",
            required=p["required"],
        )

    def canonical_form(self) -> str:
        return self.name.upper()


@dataclass
class Option(Parameter):
    opts: list[str]
    is_flag: bool

    @staticmethod
    def from_dict(p: dict[str, Any]) -> "Option":
        return Option(
            name=p["name"],
            help=dedent(p["help"]).strip(),
            required=p["required"],
            opts=p["opts"],
            is_flag=p["is_flag"],
        )

    def forms(self) -> Iterator[str]:
        for o in self.opts:
            form = o
            if not self.is_flag:
                form = f"{o} {self.name}"
            yield form

    def canonical_form(self) -> str:
        return next(self.forms())

    def to_rst_lines(self) -> Lines:
        yield self.canonical_form()
        yield indent(self.help)
        yield ""
        if aliases := [f"``{o}``" for o in self.opts[1:]]:
            yield indent(f"Aliases: {', '.join(aliases)}")
            yield ""


@dataclass
class Command:
    name: str
    help: str
    arguments: list[Argument]
    options: list[Option]
    children: list["Command"]

    def flattened(self) -> Iterator["Command"]:
        yield self
        for child in self.children:
            yield from child.flattened()

    @staticmethod
    def from_dict(command: dict[str, Any], parent: str = "") -> "Command":
        params = [p for p in command["params"] if p["name"] != "help"]
        name = command["name"]
        if parent:
            name = f"{parent} {name}"
        if name == "main":
            parent = ""
            name = ""
        else:
            parent = name

        options = [
            Option.from_dict(p) for p in params if p["param_type_name"] == "option"
        ]
        arguments = [
            Argument.from_dict(p) for p in params if p["param_type_name"] == "argument"
        ]
        children = [
            Command.from_dict(i, parent) for i in command.get("commands", {}).values()
        ]
        if children:
            arguments.append(Argument(name="command", help="", required=True))

        return Command(
            name=name,
            help=dedent(command["help"]).strip(),
            options=options,
            arguments=arguments,
            children=children,
        )

    def syntax(self) -> Lines:
        def parts() -> Iterator[str]:
            yield "circuitpython-tool"
            if self.name:
                yield self.name
            if self.options:
                yield "[OPTIONS]"
            for argument in self.arguments:
                yield argument.inline_form

        yield ".. rubric:: Syntax"
        yield ".. parsed-literal::"
        yield ""
        yield indent(" ".join(parts()))

    def help_lines(self) -> Lines:
        yield ".. rubric:: Description"
        yield ""
        yield self.help
        yield ""

    def to_rst_lines(self) -> Lines:
        if self.name:
            yield f"{self.name}"
        else:
            yield "Command Reference"
        yield "=" * 40
        yield ""
        yield from self.syntax()
        yield ""
        yield from self.help_lines()
        yield ""
        if self.options:
            yield ".. rubric:: Options"
            yield ""
            for option in self.options:
                yield from option.to_rst_lines()
                yield ""
            yield ""
        yield ""


def merge_lines(line_lists: Iterable[Iterable[str]]) -> str:
    blocks = ("\n".join(line_list) for line_list in line_lists)
    return "\n\n----\n\n".join(blocks)


def main() -> None:
    with click.Context(commands.main) as context:
        info = context.to_info_dict()["command"]
        # TODO(dhrosa): There should be a better way to refer to the docs directory.
        docs_dir = Path(__file__).parent.parent.parent.parent / "docs"
        out_path = docs_dir / "source" / "generated_cli_docs.rst"
        out_path.write_text(
            merge_lines(c.to_rst_lines() for c in Command.from_dict(info).flattened())
        )


if __name__ == "__main__":
    main()
