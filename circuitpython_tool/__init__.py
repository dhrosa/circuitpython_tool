from .cli import Cli
from .args import parse_args


def main():
    cli = Cli(parse_args())
    cli.run()


if __name__ == "__main__":
    main()
