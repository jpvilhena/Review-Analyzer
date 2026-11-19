"""Single command entry point for the review analysis application."""
import argparse
import sys
from importlib import import_module


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect", "pilot", "review"))
    if not argv:
        parser.print_help()
        return
    command = parser.parse_args(argv[:1]).command
    import_module(f"review_analyzer.cli.{command}").main(argv[1:])


if __name__ == "__main__":
    main()
