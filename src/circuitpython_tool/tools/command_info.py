import rich_click as click
from rich import print

from ..cli import commands


def main() -> None:
    """Dump ``click`` introspection data about circuitpython-tool."""
    with click.Context(commands.main) as context:
        print(context.to_info_dict()["command"])


if __name__ == "__main__":
    main()
