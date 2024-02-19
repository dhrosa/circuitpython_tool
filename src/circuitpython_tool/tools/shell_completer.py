import shlex

import rich_click as click
from click.shell_completion import ZshComplete
from rich import get_console

from circuitpython_tool.cli import commands


@click.command
@click.argument("arg_str", required=True)
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
        commands.main, {}, "circuitpython-tool", "_CIRCUITPYTHON_TOOL_COMPLETE"
    )
    args = shlex.split(arg_str)
    if arg_str.endswith(" "):
        incomplete = " "
    else:
        incomplete = args.pop()
    print(f"$ circuitpython-tool {arg_str}")

    console = get_console()
    for i, item in enumerate(complete.get_completions(args, incomplete)):
        console.print(
            f"{item.value} | {item.help}",
            markup=False,
            style="reverse" if i == 0 else None,
        )


if __name__ == "__main__":
    main()
