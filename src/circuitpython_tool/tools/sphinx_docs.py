"""
Tool for generating Sphinx documentation for the circuitpython-tool CLI.
"""

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
"""A collection of RST lines."""

indent_level: int = 0
"""Current RST indentation level."""


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


def section(title: str, level: int) -> Lines:
    """
    Render an RST section header.

    Uses the convention from
    https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html#sections
    """
    section_chars = '#*=-^"'
    line = section_chars[level] * len(title)
    if level < 2:
        # Draw an overline
        yield line
    yield title
    yield line
    yield ""


@dataclass
class Type:
    """
    A ``click`` parameter type.
    """

    name: str
    choices: list[str]
    """If this is a 'choice' type argument, the valid choices. Empty otherwise."""

    @staticmethod
    def from_dict(t: dict[str, Any]) -> "Type":
        return Type(name=t["name"], choices=t.get("choices", []))

    @property
    def label(self) -> str | None:
        """
        RST label for this type's documentation.

        Labels are defined in cli_prolog.rst
        """
        if self.name not in ("device", "query", "board_id"):
            return None
        return f"types.{self.name}"


@dataclass
class Parameter:
    """
    Superclass for arguments and options.
    """

    name: str
    help: str
    required: bool
    type: Type


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


@dataclass
class Option(Parameter):
    primary_form: str
    """The primary option name for this command; i.e. the full version."""

    aliases: list[str]

    is_flag: bool
    """If true, this option doesn't need a value."""

    negation: str | None
    """The negative version of this option. Only used for flags."""

    env_var: str | None
    """Environment variable that this option can also get its value from."""

    default: Any

    @staticmethod
    def from_dict(p: dict[str, Any]) -> "Option":
        opts = p["opts"]
        negations = p["secondary_opts"]
        return Option(
            name=p["name"],
            help=dedent(p["help"]).strip(),
            required=p["required"],
            type=Type.from_dict(p["type"]),
            primary_form=opts[0],
            aliases=opts[1:],
            is_flag=p["is_flag"],
            negation=negations[0] if negations else None,
            env_var=p["envvar"],
            default=p["default"],
        )

    def to_rst(self) -> Lines:
        """Render as an RST ``option_list_item``"""
        title_forms = [self.primary_form]
        if not self.is_flag:
            title_forms[0] += f" {self.name}"
        if self.negation:
            title_forms.append(self.negation)
        yield ", ".join(title_forms)
        yield ""

        with indented():
            priority = "Required" if self.required else "Optional"
            yield f"*{priority}*. {self.help}"
            yield ""
            # Render following properties as an RST ``field_list``
            if aliases := [f"``{a}``" for a in self.aliases]:
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
    """
    Chain of subcommand argument values that identify this command.

    e.g. [] for the top-level main function. ["uf2", "download"] for the "uf2 download" command.
    """

    help: str
    arguments: list[Argument]
    options: list[Option]
    children: list["Command"]
    linux_only: bool

    @staticmethod
    def from_dict(command: dict[str, Any], parent_path: list[str]) -> "Command":
        command_path = list[str]()
        if (name := command["name"]) != "main":
            command_path = parent_path + [name]

        arguments = list[Argument]()
        options = list[Option]()
        for param in command["params"]:
            if param["name"] == "help":
                continue
            match param["param_type_name"]:
                case "argument":
                    arguments.append(Argument.from_dict(param))
                case "option":
                    options.append(Option.from_dict(param))

        return Command(
            command_path=command_path,
            help=dedent(command["help"]).strip(),
            options=options,
            arguments=arguments,
            children=[
                Command.from_dict(i, command_path)
                for i in command.get("commands", {}).values()
            ],
            linux_only=command.get("linux_only", False),
        )

    @property
    def label(self) -> str:
        """RST label for this command."""
        return ".".join(self.command_path + ["command"])

    @property
    def options_label(self) -> str:
        """RST label for this command's options."""
        return ".".join(self.command_path + ["options"])

    @property
    def children_label(self) -> str:
        """RST label for this command's subcommand options."""
        return self.argument_label("command")

    def argument_label(self, name: str) -> str:
        """RST label for the given argument."""
        return ".".join(self.command_path + ["arguments", name])

    def to_rst(self) -> Lines:
        yield f".. _{self.label}:"
        yield ""
        yield from section(
            title=" ".join(self.command_path) or "Commands",
            level=len(self.command_path) + 1,
        )
        yield from self.syntax()
        yield from self.description()
        yield from self.arguments_rst()
        if self.options:
            yield f".. _{self.options_label}:"
            yield ".. rubric:: Options"
            yield ""
            for option in self.options:
                yield from option.to_rst()
                yield ""
            yield ""
        yield ""

    def syntax(self) -> Lines:
        """Shows basic structure of command-line invocation."""

        def parts() -> Iterator[str]:
            """Command-line components to be space-separated."""
            yield "circuitpython-tool"
            yield from self.command_path
            if self.options:
                yield f"[:ref:`OPTIONS <{self.options_label}>`]"
            if self.children:
                yield f":ref:`COMMAND <{self.children_label}>`"
            for argument in self.arguments:
                form = f":ref:`{argument.name.upper()} <{self.argument_label(argument.name)}>`"
                if not argument.required:
                    form = f"[{form}]"
                yield form

        yield ".. rubric:: Syntax"
        yield ".. parsed-literal::"
        yield ""
        with indented():
            yield " ".join(parts())

    def description(self) -> Lines:
        """Detailed text description of command."""
        yield ".. rubric:: Description"
        yield ""
        yield self.help
        yield ""
        if self.linux_only:
            yield "*Linux-only*."
            yield ""

    def arguments_rst(self) -> Lines:
        if (not self.arguments) and (not self.children):
            return
        yield ".. rubric:: Arguments"
        yield ""
        yield from self.children_rst()
        for argument in self.arguments:
            yield f".. _{self.argument_label(argument.name)}:"
            yield ""
            yield f"``{argument.name.upper()}``"
            with indented():
                # Render following properties as an RST ``field_list``
                yield f":Required: {argument.required}"
                yield ""
                type_text = argument.type.name
                if type_label := argument.type.label:
                    type_text = f":ref:`{type_label}`"
                yield f":Type: {type_text}"
                yield ""

    def children_rst(self) -> Lines:
        if not self.children:
            return
        yield f".. _{self.children_label}:"
        yield ""
        yield "``COMMAND``"
        with indented():
            yield "Valid values:"
            yield ""
            yield ".. hlist::"
            yield ""
            for child in self.children:
                with indented():
                    yield f"* :ref:`{child.command_path[-1]}<{child.label}>`"
        yield ""


def all_lines(root: Command) -> Lines:
    """RST contents for the given root command."""

    def flattened(command: Command) -> Iterator[Command]:
        """Recursively walk the command tree."""
        yield command
        for child in command.children:
            yield from flattened(child)

    hrule = "\n----\n"
    for command in flattened(root):
        yield hrule
        yield from command.to_rst()


@click.command
def main() -> None:
    """Render CLI documentation for circuitpython-tool to reStructuredText."""
    with click.Context(commands.main) as context:
        info = context.to_info_dict()["command"]
    root = Command.from_dict(info, parent_path=[])
    print(root)
    # TODO(dhrosa): There should be a better way to refer to the docs directory.
    docs_dir = Path(__file__).parent.parent.parent.parent / "docs"
    out_path = docs_dir / "source/cli/generated.rst"

    print(f"Writing to {out_path}")
    out_path.write_text(render_lines(all_lines(root)))


if __name__ == "__main__":
    main()
