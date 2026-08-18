import argparse
from pathlib import Path

from linum.src.compiler import compile_source


def main():
    parser = argparse.ArgumentParser(
        prog="linum",
        description="Linum compiler frontend",
    )

    parser.add_argument(
        "source",
        type=Path,
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    source = args.source.read_text()

    llvm = compile_source(source)

    if args.output:
        args.output.write_text(llvm)
    else:
        print(llvm)


if __name__ == "__main__":
    main()
