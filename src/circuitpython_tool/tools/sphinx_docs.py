from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent, indent
from typing import Any, TypeAlias

import rich_click as click
from rich import print

from ..cli import commands

Lines: TypeAlias = Iterable[str]

indent_level: int = 0


@contextmanager
def indented() -> Iterator[None]:
    """Lines yielded within this have their indentation increased by one additional level."""
    global indent_level
    indent_level += 1
    try:
        yield
    finally:
        indent_level -= 1


def render_lines(lines: Lines) -> str:
    """Combine lines of text together respecting indentation level."""

    def indented_lines() -> Iterable[str]:
        prefix = " " * 3
        for line in lines:
            yield indent(line, prefix * indent_level)

    return "\n".join(indented_lines())


@dataclass
class Type:
    name: str
    choices: list[str]

    @staticmethod
    def from_dict(t: dict[str, Any]) -> "Type":
        return Type(name=t["name"], choices=t.get("choices", []))


@dataclass
class Parameter:
    name: str
    help: str
    required: bool
    type: Type

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
            type=Type.from_dict(p["type"]),
        )

    def canonical_form(self) -> str:
        return self.name.upper()


@dataclass
class Option(Parameter):
    opts: list[str]
    is_flag: bool
    negation: str | None
    env_var: str | None
    default: Any

    @staticmethod
    def from_dict(p: dict[str, Any]) -> "Option":
        negations = p["secondary_opts"]
        return Option(
            name=p["name"],
            help=dedent(p["help"]).strip(),
            required=p["required"],
            type=Type.from_dict(p["type"]),
            opts=p["opts"],
            is_flag=p["is_flag"],
            negation=negations[0] if negations else None,
            env_var=p["envvar"],
            default=p["default"],
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
        title_forms = [self.canonical_form()]
        if self.negation:
            title_forms.append(self.negation)
        yield ", ".join(title_forms)
        yield ""

        with indented():
            help_prefix = "Required" if self.required else "Optional"
            yield f"*{help_prefix}*. {self.help}"
            yield ""
            if aliases := [f"``{o}``" for o in self.opts[1:]]:
                yield f":Aliases: {', '.join(aliases)}"
            if self.env_var:
                yield f":Environment Variable: ``{self.env_var}``"
            if choices := [f"``{c}``" for c in self.type.choices]:
                yield f":Choices: {', '.join(choices)}"
            elif not self.is_flag:
                yield f":Type: {self.type.name}"
            if self.default is not None:
                yield f":Default: ``{self.default}``"
        yield ""


@dataclass
class Command:
    command_path: list[str]
    help: str
    arguments: list[Argument]
    options: list[Option]
    children: list["Command"]

    @property
    def name(self) -> str:
        return " ".join(self.command_path)

    @staticmethod
    def from_dict(command: dict[str, Any], parent_path: list[str]) -> "Command":
        command_path = list[str]()
        if (name := command["name"]) != "main":
            command_path = parent_path + [name]
        params = [p for p in command["params"] if p["name"] != "help"]
        options = [
            Option.from_dict(p) for p in params if p["param_type_name"] == "option"
        ]
        arguments = [
            Argument.from_dict(p) for p in params if p["param_type_name"] == "argument"
        ]
        children = [
            Command.from_dict(i, command_path)
            for i in command.get("commands", {}).values()
        ]
        if children:
            # Add "command" pseudo-argument
            arguments.append(
                Argument(
                    name="command",
                    help="",
                    required=True,
                    type=Type(
                        name="command",
                        choices=[],
                    ),
                )
            )

        return Command(
            command_path=command_path,
            help=dedent(command["help"]).strip(),
            options=options,
            arguments=arguments,
            children=children,
        )

    @property
    def label(self) -> str:
        return "command-" + "-".join(self.command_path)

    def section(self) -> Lines:
        section_chars = '#*=-^"'
        depth = len(self.command_path)
        line = section_chars[depth] * 40

        # Draw overline on levels 0 and 1
        if depth < 2:
            yield line
        yield self.name or "Commands"
        yield line

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
        with indented():
            yield " ".join(parts())

    def description(self) -> Lines:
        yield ".. rubric:: Description"
        yield ""
        yield self.help
        yield ""
        if not self.children:
            return
        yield "``COMMAND`` choices:"
        yield ""
        with indented():
            yield ".. hlist::"
            yield ""
            for child in self.children:
                with indented():
                    yield f"* :ref:`{child.command_path[-1]}<{child.label}>`"
            yield ""

    def to_rst_lines(self) -> Lines:
        yield f".. _{self.label}:"
        yield ""
        yield from self.section()
        yield ""
        yield from self.syntax()
        yield ""
        yield from self.description()
        yield ""
        if self.options:
            yield ".. rubric:: Options"
            yield ""
            for option in self.options:
                yield from option.to_rst_lines()
                yield ""
            yield ""
        yield ""


def all_lines(root: Command) -> Lines:
    yield "#" * 40
    yield "Overview"
    yield "#" * 40
    yield "TODO"
    yield ""

    def flattened(command: Command) -> Iterator[Command]:
        yield command
        for child in command.children:
            yield from flattened(child)

    for command in flattened(root):
        yield "\n----\n"
        yield from command.to_rst_lines()


def main() -> None:
    with click.Context(commands.main) as context:
        info = context.to_info_dict()["command"]
    root = Command.from_dict(info, [])
    print(root)
    # TODO(dhrosa): There should be a better way to refer to the docs directory.
    docs_dir = Path(__file__).parent.parent.parent.parent / "docs"
    out_path = docs_dir / "source" / "generated_cli_docs.rst"
    out_path.write_text(render_lines(all_lines(root)))


if __name__ == "__main__":
    main()
