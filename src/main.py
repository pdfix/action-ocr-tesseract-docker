import argparse
import os
import sys
from pathlib import Path

from tesseract import ocr


def set_arguments(
    parser: argparse.ArgumentParser, names: list, required_output: bool = True, output_help: str = ""
) -> None:
    """
    Set arguments for the parser based on the provided names and options.

    Args:
        parser (argparse.ArgumentParser): The argument parser to set arguments for.
        names (list): List of argument names to set.
        required_output (bool): Whether the output argument is required. Defaults to True.
        output_help (str): Help message for the output argument. Defaults to an empty string.
    """
    for name in names:
        match name:
            case "input":
                parser.add_argument("--input", "-i", type=str, required=True, help="The input PDF file")
            case "key":
                parser.add_argument("--key", type=str, help="PDFix license key")
            case "lang":
                parser.add_argument(
                    "--lang",
                    type=str,
                    default="",
                    help="Language identifier",
                )
            case "name":
                parser.add_argument("--name", type=str, help="PDFix license name")
            case "output":
                parser.add_argument("--output", "-o", type=str, required=required_output, help=output_help)


def run_config_subcommand(args) -> None:
    get_pdfix_config(args.output)


def get_pdfix_config(path: str) -> None:
    """
    If Path is not provided, output content of config.
    If Path is provided, copy config to destination path.

    Args:
        path (string): Destination path for config.json file
    """
    config_path = os.path.join(Path(__file__).parent.absolute(), "../config.json")

    with open(config_path, "r", encoding="utf-8") as file:
        if path is None:
            print(file.read())
        else:
            with open(path, "w") as out:
                out.write(file.read())


def run_ocr_subcommand(args) -> None:
    if not os.path.isfile(args.input):
        raise Exception(f"Error: The input file '{args.input}' does not exist.")

    if args.input.lower().endswith(".pdf") and args.output.lower().endswith(".pdf"):
        ocr(args.input, args.output, args.name, args.key, args.lang)
    else:
        raise Exception("Input and output file must be PDF")


def ocr_file(input_file: str, output_file: str, name: str, key: str, lang: str) -> None:
    """
    Run OCR on a PDF file using Tesseract.
    Args:
        input_file (str): Path to the input PDF file.
        output_file (str): Path to the output PDF file.
        name (str): PDFix license name.
        key (str): PDFix license key.
        lang (str): Language identifier for OCR Tesseract.
    """
    ocr(input_file, output_file, name, key, lang)


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser(
        description="Process a PDF or image with Tesseract OCR",
    )
    parser.add_argument("--name", type=str, default="", help="license name")
    parser.add_argument("--key", type=str, default="", help="license key")

    subparsers = parser.add_subparsers(dest="subparser")

    # Config subparser
    config_subparser = subparsers.add_parser(
        "config",
        help="Extract config file for integration",
    )
    set_arguments(
        config_subparser,
        ["output"],
        False,
        "Output to save the config JSON file. Application output" + "is used if not provided",
    )
    config_subparser.set_defaults(func=run_config_subcommand)

    # OCR subparser
    ocr_subparser = subparsers.add_parser(
        "ocr",
        help="Run ocr in PDF document with predefined language.",
    )
    set_arguments(ocr_subparser, ["name", "key", "input", "output", "lang"], True, "The output PDF file")
    ocr_subparser.set_defaults(func=run_ocr_subcommand)

    # Parse arguments
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 0:  # This happens when --help is used, exit gracefully
            sys.exit(0)
        print("Failed to parse arguments. Please check the usage and try again.")
        sys.exit(1)

    # Run subcommand
    try:
        args.func(args)
    except Exception as e:
        print(f"Failed to run the program: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
