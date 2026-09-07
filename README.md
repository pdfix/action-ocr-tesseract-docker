# OCR Tesseract

A Docker image that adds an OCR text layer to PDF files using PDFix SDK and Tesseract OCR. For PDF output, a **PDFix SDK** license is required.

## Table of Contents

- [OCR Tesseract](#ocr-tesseract)
  - [Getting started](#getting-started)
  - [Usage](#usage)
  - [Commands](#commands)
  - [Arguments](#arguments)
  - [Params JSON](#params-json)
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

- `ocr`: OCR a scanned PDF page-by-page (PDF → PDF)
- `ocr-content`: OCR filtered page content and place an invisible text Form XObject per page (PDF → PDF)

## Arguments

### Common

| Option | Required | Type / expected value | Description |
|---|:---:|---|---|
| `--input`, `-i` | yes | Path to an existing `.pdf` file | Input PDF |
| `--output`, `-o` | yes | Path for the output `.pdf` file | Output PDF |
| `--lang` | no | Tesseract language code string (e.g. `eng`); empty uses default handling | OCR language |
| `--name` | no | String (PDFix account license name) | PDFix license name |
| `--key` | no | String (PDFix account license key) | PDFix license key |

### `ocr`

Uses the [Common](#common) arguments.

### `ocr-content`

Uses the [Common](#common) arguments, plus:

| Option | Required | Type / expected value | Description |
|---|:---:|---|---|
| `--params` | yes | Path to a `.json` file | Object filter parameters (see [Params JSON](#params-json)) |

## Params JSON

`--params` is a JSON array of parameter objects with at least `name` and `value`. For `ocr-content`, `object_types` is an ECMAScript regex matching page object types (e.g. `"^pds_image$"`, or `".*"` for all), or a template `object_update` object.

See `tests/params_content.json`, `tests/params_content_template.json`, and `example/first_page_image_content_template.json` (first-page images; load into Desktop params).

## Examples

OCR a scanned PDF:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/ocr-tesseract:latest \
  ocr --name "${LICENSE_NAME}" --key "${LICENSE_KEY}" \
  -i /data/scanned.pdf -o /data/ocr.pdf --lang eng
```

OCR filtered page content:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/ocr-tesseract:latest \
  ocr-content --name "${LICENSE_NAME}" --key "${LICENSE_KEY}" \
  -i /data/input.pdf -o /data/output.pdf --lang eng \
  --params /data/params_content.json
```

## Help & support

For PDFix SDK licensing or issues, contact `support@pdfix.net`.

## Licenses

- [PDFix Terms](https://pdfix.net/terms)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)

Trial versions of the PDFix SDK may apply watermarks and redact random content in the output PDF.
