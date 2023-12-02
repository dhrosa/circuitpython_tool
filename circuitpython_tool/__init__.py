from .cli import parse_args, Cli

def main():
    cli = Cli(parse_args())
    cli.run()

if __name__ == "__main__":
    main()
