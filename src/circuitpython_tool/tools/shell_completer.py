import shlex

import rich_click as click
from click.shell_completion import ZshComplete
from rich import print
from rich.text import Text

from ..cli import commands


@click.command
@click.argument("arg_str", default="")
def main(arg_str: str) -> None:
    """Simulate a shell requesting completion.

    The arguments is forwarded to circuitpython-tool as an incomplete
    commandline for completion and completions are printed to stdout. The first
    completion is highlighted as if a user at a shell was selecting it.

    If ARG_STR ends in a space, the earlier parts of the string are interpreted
    as complete arguments, and that the user is requesting completion for the
    first character of the next argument.

    If ARG_STR does not end in a space, then the last argument will be the
    argument to be completed.
    """
    complete = ZshComplete(
        commands.main,
        commands.main.context_settings,
        commands.PROGRAM_NAME,
        commands.COMPLETE_VAR,
    )
    if not arg_str:
        arg_str = " "
    args = shlex.split(arg_str)
    if arg_str.endswith(" "):
        incomplete = ""
    else:
        incomplete = args.pop()

    # Emulate a user a terminal
    print(
        Text.assemble(
            ("$", "green bold"),
            " circuitpython-tool ",
            arg_str,
            # Fake cursor at end of input
            (" ", "reverse"),
        )
    )

    for i, item in enumerate(complete.get_completions(args, incomplete)):
        item_str = f"{item.value} | {item.help}" if item.help else item.value
        print(Text(item_str, style="reverse" if i == 0 else ""))


if __name__ == "__main__":
    main()
