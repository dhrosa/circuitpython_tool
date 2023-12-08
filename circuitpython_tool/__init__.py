from .args import parse_args
from .cli import Cli


def main():
    cli = Cli(parse_args())
    cli.run()


if __name__ == "__main__":
    main()
