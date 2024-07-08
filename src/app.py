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

    args = parser.parse_args()

    if not args.input or not args.output:
        parser.error("The following arguments are required: -i/--input, -o/--output")

    input_file = args.input
    output_file = args.output

    if not os.path.isfile(input_file):
        print(f"Error: The input file '{input_file}' does not exist.")
        return

    if input_file.lower().endswith(".pdf"):
        ocr(input_file, output_file)
    else:
        print("Input file must be PDF")


if __name__ == "__main__":
    main()
