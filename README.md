# OCR Tesseract

A Docker image that adds an OCR text layer to scanned PDF files using PDFix SDK and Tesseract OCR.

## Table of Contents

- [OCR Tesseract](#ocr-tesseract)
  - [Getting started](#getting-started)
  - [Usage](#usage)
  - [Commands](#commands)
  - [Arguments](#arguments)
  - [Examples](#examples)
  - [Help \& support](#help--support)
  - [Licenses](#licenses)

## Getting started

You need Docker installed. The first run downloads the image and may take longer than later runs.

## Usage

Mount a folder into the container and run a subcommand:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/ocr-tesseract:latest <command> [options]
```

## Commands

- `ocr`: OCR a scanned PDF (PDF → PDF)

## Arguments

### `ocr`

| Option | Required | Type / expected value | Description |
|---|:---:|---|---|
| `--input`, `-i` | yes | Path to an existing `.pdf` file | Input PDF |
| `--output`, `-o` | yes | Path for the output `.pdf` file | Output PDF |
| `--lang` | no | Tesseract language code string (e.g. `eng`); empty uses default handling | OCR language |
| `--name` | no | String (PDFix account license name) | PDFix license name |
| `--key` | no | String (PDFix account license key) | PDFix license key |

## Examples

OCR a scanned PDF:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/ocr-tesseract:latest \
  ocr --name "${LICENSE_NAME}" --key "${LICENSE_KEY}" \
  -i /data/scanned.pdf -o /data/ocr.pdf --lang eng
```

## Help & support

For PDFix SDK licensing or issues, contact `support@pdfix.net`.

## Licenses

- [PDFix Terms](https://pdfix.net/terms)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract/)
