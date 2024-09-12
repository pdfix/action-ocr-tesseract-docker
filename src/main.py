import argparse
import os
import shutil
import sys
from pathlib import Path

from tesseract import ocr

def get_config(path) -> None:    
    if path is None:
        with open(os.path.join(Path(__file__).parent.absolute(), "../config.json"), 'r') as f:
            print(f.read())    
    else:
        src = os.path.join(Path(__file__).parent.absolute(), "../config.json")
        dst = path
        shutil.copyfile(src, dst)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process a PDF or image with Tesseract OCR",
    )
    parser.add_argument("--name", type=str, default="", help="license name")
    parser.add_argument("--key", type=str, default="", help="license key")

    subparsers = parser.add_subparsers(dest="subparser")

    # get config subparser
    pars_config = subparsers.add_parser("config")
    pars_config.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output to save the config JSON file. Application output is used if not provided",
    )    

    pars_ocr = subparsers.add_parser("ocr", help="Run ocr in PDF document with predefined language.")

    pars_ocr.add_argument("-i", "--input", type=str, help="The input PDF file")
    pars_ocr.add_argument(
        "-o",
        "--output",
        type=str,
        help="The output PDF file",
    )
    pars_ocr.add_argument(
        "--lang",
        type=str,
        default="",
        help="Language identifier",
    )

    args = parser.parse_args()

    if args.subparser == "config":
        get_config(args.output)
        sys.exit(0)
    elif args.subparser == "ocr":    

        if not args.input or not args.output:
            parser.error("The following arguments are required: -i/--input, -o/--output")

        input_file = args.input
        output_file = args.output

        if not os.path.isfile(input_file):
            sys.exit(f"Error: The input file '{input_file}' does not exist.")
            return

        if input_file.lower().endswith(".pdf") and output_file.lower().endswith(".pdf"):
            try:
                ocr(input_file, output_file, args.name, args.key, args.lang)
            except Exception as e:
                sys.exit("Failed to run OCR: {}".format(e))

        else:
            print("Input and output file must be PDF")


if __name__ == "__main__":
    main()
