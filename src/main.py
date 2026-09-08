import argparse
import json
import os
import sys
import tempfile
import threading
import traceback
from pathlib import Path
from typing import Any

from constants import CONFIG_FILE
from exceptions import (
    EC_ARG_GENERAL,
    MESSAGE_ARG_GENERAL,
    ArgumentInputMissingException,
    ArgumentInputPdfOutputPdfException,
    ExpectedException,
    InvalidRegexOrTemplateException,
)
from image_update import DockerImageContainerUpdateChecker
from ocr_content import OcrContent
from ocr_document import OcrDocument
from params_parser import ParamsParser


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
                parser.add_argument("--key", type=str, default="", nargs="?", help="PDFix license key")
            case "lang":
                parser.add_argument(
                    "--lang",
                    type=str,
                    default="",
                    help="Language identifier",
                )
            case "name":
                parser.add_argument("--name", type=str, default="", nargs="?", help="PDFix license name")
            case "output":
                parser.add_argument("--output", "-o", type=str, required=required_output, help=output_help)
            case "params":
                parser.add_argument(
                    "--params", type=str, required=True, help="Path to JSON file with filled parameters."
                )


def run_config_subcommand(args) -> None:
    get_pdfix_config(args.output)


def get_pdfix_config(path: str) -> None:
    """
    If Path is not provided, output content of config.
    If Path is provided, copy config to destination path.

    Args:
        path (string): Destination path for config.json file
    """
    config_path: Path = Path(__file__).parent.parent.joinpath(CONFIG_FILE).resolve()

    with open(config_path, "r", encoding="utf-8") as file:
        if path is None:
            print(file.read())
        else:
            with open(path, "w") as out:
                out.write(file.read())


def run_ocr_subcommand(args) -> None:
    zoom: float = 2.0

    if not os.path.isfile(args.input):
        raise ArgumentInputMissingException()

    if args.input.lower().endswith(".pdf") and args.output.lower().endswith(".pdf"):
        ocr_file(args.input, args.output, args.name, args.key, args.lang, zoom)
    else:
        raise ArgumentInputPdfOutputPdfException()


def ocr_file(input_file: str, output_file: str, name: str, key: str, lang: str, zoom: float) -> None:
    """
    Run OCR on a PDF file using Tesseract.

    Args:
        input_file (str): Path to the input PDF file.
        output_file (str): Path to the output PDF file.
        name (str): PDFix license name.
        key (str): PDFix license key.
        lang (str): Language identifier for OCR Tesseract.
        zoom (float): Zoom level for rendering the page.
    """
    ocr_document = OcrDocument(name, key, input_file, output_file, lang, zoom)
    ocr_document.ocr()


def run_ocr_content_subcommand(args) -> None:
    zoom: float = 2.0

    if not os.path.isfile(args.input):
        raise ArgumentInputMissingException(args.input)

    if not (args.input.lower().endswith(".pdf") and args.output.lower().endswith(".pdf")):
        raise ArgumentInputPdfOutputPdfException()

    params_parser = ParamsParser(args.params)
    params_parser.parse()
    object_types: Any = params_parser.params.get("object_types")
    if isinstance(object_types, str):
        ocr_content_file(
            args.input,
            args.output,
            args.name,
            args.key,
            args.lang,
            zoom,
            object_types,
        )
    elif isinstance(object_types, dict):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json") as template_file:
            with open(template_file.name, "w", encoding="utf-8") as template_file_write:
                json.dump(object_types, template_file_write)
            ocr_content_file(
                args.input,
                args.output,
                args.name,
                args.key,
                args.lang,
                zoom,
                Path(template_file.name),
            )
    else:
        raise InvalidRegexOrTemplateException()


def ocr_content_file(
    input_file: str,
    output_file: str,
    name: str,
    key: str,
    lang: str,
    zoom: float,
    regex_template: str | Path,
) -> None:
    """
    Run content-filtered OCR on a PDF file using Tesseract.

    Args:
        input_file (str): Path to the input PDF file.
        output_file (str): Path to the output PDF file.
        name (str): PDFix license name.
        key (str): PDFix license key.
        lang (str): Language identifier for OCR Tesseract.
        zoom (float): Zoom level for rendering the page.
        regex_template (str | Path): Regex or path to a template JSON file.
    """
    ocr_content = OcrContent(name, key, input_file, output_file, regex_template, lang, zoom)
    ocr_content.ocr_content()


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

    # OCR content subparser
    ocr_content_subparser = subparsers.add_parser(
        "ocr-content",
        help="Run OCR on filtered page content and place a text Form XObject per page.",
    )
    set_arguments(
        ocr_content_subparser,
        ["name", "key", "input", "output", "lang", "params"],
        True,
        "The output PDF file",
    )
    ocr_content_subparser.set_defaults(func=run_ocr_content_subcommand)

    # Parse arguments
    try:
        args = parser.parse_args()
    except ExpectedException as e:
        print(e.message, file=sys.stderr)
        sys.exit(e.error_code)
    except SystemExit as e:
        if e.code != 0:
            print(MESSAGE_ARG_GENERAL, file=sys.stderr)
            sys.exit(EC_ARG_GENERAL)
        # This happens when --help is used, exit gracefully
        sys.exit(0)
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        print(f"Failed to run the program: {e}", file=sys.stderr)
        sys.exit(1)

    if hasattr(args, "func"):
        # Check for updates only when help is not checked
        update_checker = DockerImageContainerUpdateChecker()
        # Check it in separate thread not to be delayed when there is slow or no internet connection
        update_thread = threading.Thread(target=update_checker.check_for_image_updates)
        update_thread.start()

        # Run subcommand
        try:
            args.func(args)
        except ExpectedException as e:
            print(e.message, file=sys.stderr)
            sys.exit(e.error_code)
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            print(f"Failed to run the program: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            # Make sure to let update thread finish before exiting
            update_thread.join()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
