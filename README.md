# OCR Tesseract 

A Docker image that adds an OCR text layer to scanned PDF files using PDFix SDK and Tesseract OCR.

## Table of Contents

- [OCR Tesseract](#ocr-tesseract)
  - [Table of Contents](#table-of-contents)
  - [Getting Started](#getting-started)
  - [Run using Command Line Interface](#run-using-command-line-interface)
  - [Exporting Configuration for Integration](#exporting-configuration-for-integration)
  - [License \& libraries used](#license--libraries-used)
  - [Help \& Support](#help--support)
  

## Getting Started

To use this Docker application, you'll need to have Docker installed on your system. If Docker is not installed, please follow the instructions on the [official Docker website](https://docs.docker.com/get-docker/) to install it.

## Run using Command Line Interface

To run docker container as CLI you should share the folder with PDF to process using `-v` parameter. In this example it's current folder.

```bash
docker run -v $(pwd):/data/ -w /data/ pdfix/ocr-tesseract:latest ocr -i scanned.pdf -o ocr.pdf --lang eng 
```

With PDFix License add these arguments.

```bash
--name ${LICENSE_NAME} --key ${LICENSE_KEY}
```

First run will pull the docker image, which may take some time. Make your own image for more advanced use.

For more detailed information about the available command-line arguments, you can run the following command:

```bash
docker run --rm pdfix/ocr-tesseract:latest --help
```

### Exporting Configuration for Integration

To export the configuration JSON file, use the following command:

```bash
docker run -v $(pwd):/data -w /data --rm pdfix/ocr-tesseract:latest config -o config.json
```

## License & libraries used

- PDFix SDK - https://pdfix.net/terms
- OCR Tesseract - https://github.com/tesseract-ocr/tesseract/

Trial version of the PDFix SDK may apply a watermark on the page and redact random parts of the PDF including the scanned image in background. Contact us to get an evaluation or production license.

## Help & Support

To obtain a PDFix SDK license or report an issue please contact us at support@pdfix.net.
For more information visit https://pdfix.net
