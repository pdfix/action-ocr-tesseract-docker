import argparse
import os

from tesseract import ocr


def main():
    parser = argparse.ArgumentParser(
        description="Process a PDF or image file with Tesseract OCR"
    )
    parser.add_argument("-i", "--input", type=str, help="The input PDF or image file")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="The output file (either .txt or .json)",
    )
    parser.add_argument(
        "-l",
        "--lang",
        type=str,
        default="eng",
        help="Language identifier",
    )

    parser.add_argument("--name", type=str, default="", help="Pdfix license name")
    parser.add_argument("--key", type=str, default="", help="Pdfix license key")
    args = parser.parse_args()

    if not args.input or not args.output:
        parser.error("The following arguments are required: -i/--input, -o/--output")

    input_file = args.input
    output_file = args.output

    if not os.path.isfile(input_file):
        print(f"Error: The input file '{input_file}' does not exist.")
        return

    if input_file.lower().endswith(".pdf"):
        try:
            ocr(input_file, output_file, args.name, args.key)
        except Exception as e:
            print("Failed to run: {}".format(e))

    else:
        print("Input file must be PDF")


if __name__ == "__main__":
    main()
