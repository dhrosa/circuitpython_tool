import os
import shlex

import rich_click as click
from click.shell_completion import ZshComplete
from rich import get_console

from circuitpython_tool.cli import commands


@click.command(
    context_settings=dict(allow_extra_args=True, ignore_unknown_options=True)
)
@click.pass_context
def main(context: click.Context) -> None:
    """Simulate a shell requesting completion.

    All arguments are forwarded to circuitpython-tool for completion and
    completions are printed to stdout. The first completion is highlighted as if
    a user at a shell was selecting it.
    """
    os.environ.update(
        _CIRCUITPYTHON_TOOL_COMPLETE="zsh_complete",
        COMP_WORDS=shlex.join(context.args),
        COMP_CWORD=str(len(context.args) - 1),
    )
    complete = ZshComplete(
        commands.main, {}, "circuitpython-tool", "_CIRCUITPYTHON_TOOL_COMPLETE"
    )
    console = get_console()
    for i, item in enumerate(complete.get_completions(*complete.get_completion_args())):
        console.print(
            f"{item.value} - {item.help}",
            markup=False,
            style="reverse" if i == 0 else None,
        )


if __name__ == "__main__":
    main()
