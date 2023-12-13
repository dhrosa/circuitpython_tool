from .args import parse_args
from .cli import run


def main():
    run(parse_args())


if __name__ == "__main__":
    main()
